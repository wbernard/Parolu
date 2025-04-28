# meson.build im Ordner patches

pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'patches'


# Installiere den patch
patches = [

    'espeak.patch',
]

foreach ptch : patches
    install_data(
        ptch,
        install_dir: moduledir  # Installations pfad
    )
endforeach