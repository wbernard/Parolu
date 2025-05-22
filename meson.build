project('parolu', ['c', 'cpp'],
  version: '0.1.0',
  meson_version: '>= 0.63.0',
  default_options: ['warning_level=2', 'cpp_std=c++17']
)

i18n = import('i18n')
gnome = import('gnome')
python_mod = import('python')
python = python_mod.find_installation('python3')

# Installiere Wrapper
install_data('bin/parolu', install_dir: '/app/bin')

# Installiere alle Python-Quelldateien aus src/
python.install_sources(
  ['src/main.py', 'src/window.py', 'src/__init__.py', 'src/reader.py', 'src/pipervoice.py', 'src/window.ui', 'src/vocx.py'
  ],
  subdir: 'parolu'
)

# Python & Pybind11
pybind11_dep = dependency('pybind11', required: true)

# Espeak-ng
espeak_dep = dependency('', required: false)  # Dummy-Dependency

# Manuelle Suche für Flatpak
if meson.is_subproject() or get_option('prefix') == '/app'
  message('Flatpak-Build erkannt, verwende manuelle espeak-Konfiguration')
  espeak_dep = declare_dependency(
    include_directories: include_directories('/app/include'),
    link_args: ['-lespeak-ng']
  )
else
  # Normale Systeminstallation
  espeak_dep = dependency('espeak-ng', required: true)
endif

# ONNX Runtime (manuell)
onnx_dep = declare_dependency(
  include_directories: include_directories('/app/include'),
  link_args: ['-lonnxruntime']
)

# piper-phonemize (Header und Linker)
phonemize_dep = declare_dependency(
  include_directories: include_directories('/app/include'),
  link_args: ['-lpiper_phonemize']
)

# piper (Subproject)
piper_proj = subproject('piper-src',
    default_options: [
      'cpp_std=c++17'
    ]
)
piper_dep = piper_proj.get_variable('piper_dep')

# Python-Modul erstellen
python = import('python').find_installation('python3')
python.extension_module(
    'piper',
    'src/piper.cpp',  # Pfad zu Ihrer piper.cpp
    dependencies: [pybind11_dep, piper_dep],
    install: true,
    subdir: 'parolu',  # Wird zu `/app/lib/python3.X/site-packages/parolu/piper.so`
    cpp_args: ['-std=c++17']
)

# Übersetzungen und Ressourcen
subdir('data')
subdir('po')
subdir('patches')

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
