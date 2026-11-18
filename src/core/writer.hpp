#pragma once
// Writes files on a worker thread, so a save never stalls a frame (CLAUDE.md: nothing on the main
// thread may block for more than a frame). Each write is atomic and durable (writeFileAtomic);
// a newer text for a file replaces one still waiting. Outcomes come back through poll().

#include <condition_variable>
#include <deque>
#include <expected>
#include <filesystem>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

namespace lc {

class FileWriter {
public:
    FileWriter();
    // Writes whatever is still waiting, then stops.
    ~FileWriter();
    FileWriter(const FileWriter&) = delete;
    FileWriter& operator=(const FileWriter&) = delete;

    void write(std::filesystem::path file, std::string text);
    // Waits until every write asked for so far has finished.
    void flush();
    // The first failure among the writes finished since the last call (empty: none failed), and
    // whether any finished at all.
    struct Outcome {
        bool finished = false;
        std::optional<std::string> error;
    };
    [[nodiscard]] Outcome poll();

private:
    void run(const std::stop_token& stop);

    struct Job {
        std::filesystem::path file;
        std::string text;
    };
    std::mutex mutex_;
    std::condition_variable_any wake_;
    std::condition_variable idle_;
    std::deque<Job> pending_;
    bool busy_ = false;
    Outcome done_;
    std::jthread thread_; // last: started after everything it uses
};

} // namespace lc
