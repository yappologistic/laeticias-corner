#include "core/writer.hpp"

#include "core/save.hpp"

#include <algorithm>

namespace lc {

FileWriter::FileWriter() : thread_([this](const std::stop_token& stop) { run(stop); }) {}

FileWriter::~FileWriter() {
    flush();
    thread_.request_stop();
    wake_.notify_all();
}

void FileWriter::write(std::filesystem::path file, std::string text) {
    {
        const std::scoped_lock lock(mutex_);
        const auto it = std::ranges::find(pending_, file, &Job::file);
        if (it != pending_.end())
            it->text = std::move(text);
        else
            pending_.push_back({std::move(file), std::move(text)});
    }
    wake_.notify_one();
}

void FileWriter::flush() {
    std::unique_lock lock(mutex_);
    idle_.wait(lock, [&] { return pending_.empty() && !busy_; });
}

FileWriter::Outcome FileWriter::poll() {
    const std::scoped_lock lock(mutex_);
    return std::exchange(done_, Outcome{});
}

void FileWriter::run(const std::stop_token& stop) {
    std::unique_lock lock(mutex_);
    while (true) {
        wake_.wait(lock, stop, [&] { return !pending_.empty(); });
        if (pending_.empty()) return; // asked to stop with nothing left to write
        Job job = std::move(pending_.front());
        pending_.pop_front();
        busy_ = true;
        lock.unlock();
        const auto r = writeFileAtomic(job.file, job.text);
        lock.lock();
        busy_ = false;
        done_.finished = true;
        if (!r && !done_.error) done_.error = r.error();
        if (pending_.empty()) idle_.notify_all();
    }
}

} // namespace lc
