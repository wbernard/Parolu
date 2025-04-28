#include "piper_api.h"
#include "src/cpp/piper.hpp"

#include <algorithm>
#include <optional>
#include <fstream>
#include <stdexcept>

struct piper_api::ctx {
    piper::PiperConfig config;
    piper::Voice voice;
};

piper_api::piper_api(std::string model_path, std::string model_config_path,
                     std::string espeak_ng_data_path, int64_t speaker_id) {
    m_ctx = std::make_unique<ctx>();
    m_ctx->config.eSpeakDataPath = std::move(espeak_ng_data_path);
    piper::initialize(m_ctx->config);

    std::optional<piper::SpeakerId> speaker;
    if (speaker_id > -1)
        speaker.emplace(speaker_id);

    piper::loadVoice(m_ctx->config, std::move(model_path), std::move(model_config_path), m_ctx->voice, speaker);
}

piper_api::~piper_api() {
    piper::terminate(m_ctx->config);
}

float piper_api::length_scale() const {
    return m_ctx->voice.synthesisConfig.lengthScale;
}

std::vector<int16_t> piper_api::text_to_audio(std::string text, float length_scale) {
    std::vector<int16_t> out_buf;
    std::vector<int16_t> tmp_buf;
    piper::SynthesisResult result;

    m_ctx->voice.synthesisConfig.lengthScale = length_scale;

    piper::textToAudio(m_ctx->config, m_ctx->voice, std::move(text), tmp_buf, result, [&] {
        out_buf.insert(out_buf.end(), tmp_buf.begin(), tmp_buf.end());
    });

    return out_buf;
}

void piper_api::text_to_wav_file(std::string text, const std::string& wav_file_path, float length_scale) {
    std::ofstream out_file{wav_file_path, std::ios::out};

    if (!out_file)
        throw std::runtime_error("failed to open file");

    piper::SynthesisResult result;
    m_ctx->voice.synthesisConfig.lengthScale = length_scale;

    piper::textToWavFile(m_ctx->config, m_ctx->voice, std::move(text), out_file, result);
}

