#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "piper_api.h"

namespace py = pybind11;

PYBIND11_MODULE(piper, m) {
    py::class_<piper_api>(m, "piper_api")
        .def(py::init<std::string, std::string, std::string, int64_t>(),
             py::arg("model_path"),
             py::arg("config_path"),
             py::arg("espeak_data_path") = "",
             py::arg("speaker_id") = -1)
        .def("length_scale", &piper_api::length_scale)
        .def("text_to_audio", &piper_api::text_to_audio)
        .def("text_to_wav_file", &piper_api::text_to_wav_file);
}

