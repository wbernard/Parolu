project('piper', ['cpp'],
  version: '1.0.0',
  default_options: ['cpp_std=c++17']
)

# Quell-Dateien
piper_sources = files(
  'src/cpp/piper.cpp',
  'src/cpp/main.cpp'
)

pybind11_dep = dependency('pybind11', required: true)
onnx_dep = dependency('onnxruntime', required: false)
espeak_dep = dependency('espeak-ng', required: false)

# Include-Pfade
piper_inc = include_directories('src/cpp/utf8')
onnx_inc = include_directories('/app/include', '/app/include/onnxruntime')

if not onnx_dep.found()
  onnx_dep = declare_dependency(
    link_args: ['-L/app/lib', '-lonnxruntime'],
    include_directories: onnx_inc
  )
endif

phonemize_dep = declare_dependency(
  include_directories: include_directories('/app/include'),
  link_args: ['-lpiper_phonemize']
)

# Bibliothek bauen
piper_lib = library('piper',
  piper_sources,
  include_directories: [piper_inc, onnx_inc],
  dependencies: [pybind11_dep, onnx_dep, phonemize_dep, espeak_dep],
  install: true
)

# Dependency-Objekt
piper_dep = declare_dependency(
  include_directories: include_directories('src/cpp'),
  link_with: piper_lib
)
piper_inc = include_directories('src/cpp')
meson.override_dependency('piper', piper_dep)