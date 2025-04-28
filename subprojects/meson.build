project('piper', 'cpp',
  version: '1.2.0',
  default_options: [
    'cpp_std=c++17',
    'warning_level=1',
    'default_library=static'
  ]
)

# Zuerst Abhängigkeiten definieren
pybind11_dep = dependency('pybind11')
onnx_dep = dependency('onnxruntime', required: false)

if not onnx_dep.found()
  # Fallback für ONNX
  onnx_dep = declare_dependency(
    include_directories: include_directories('/app/include/onnxruntime'),
    link_args: ['-lonnxruntime']
  )
endif

piper_sources = files(
  'src/piper.cpp',
  'src/cpp/main.cpp'
)

includes = include_directories('include')

piper_lib = library(
  'piper-src',
  piper_sources,
  dependencies: [pybind11_dep, onnx_dep],
  install: true
)

piper_dep = declare_dependency(
  include_directories: includes,
  link_with: piper_lib,
  dependencies: [pybind11_dep, onnx_dep]
)