#ifndef PIPER_API_H
#define PIPER_API_H

#define PIPER_API_EXPORT __attribute__((visibility("default")))

#include <string>
#include <vector>
#include <memory>

class PIPER_API_EXPORT piper_api {
public:
    piper_api(std::string model_path, std::string model_config_path,
              std::string espeak_ng_data_path = {}, int64_t speaker_id = -1);
    ~piper_api();
    float length_scale() const;
    std::vector<int16_t> text_to_audio(std::string text, float length_scale = 1.0f);
    void text_to_wav_file(std::string text, const std::string& wav_file_path, float length_scale = 1.0f);

private:
    struct ctx;
    std::unique_ptr<ctx> m_ctx;
};

#endif

