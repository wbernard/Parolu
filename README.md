# parolu

Ein einfaches Werkzeug um Text in Sprache umzuwandeln. 
Zwei Esperanto-Stimmen werden mit der Anwendung mitgeliefert,
weil es aktuell keine geeigneten Esperanto-Stimmen zum Herunterladen gibt.
Bei den anderen Sprachen muss vorher mindestens eine Stimme heruntergeladen werden.

## Setting up translations

1. Create `/build` directory with `meson setup builddir`
2. `cd /build`
3. `ninja parolu-pot`

## Updating translation files

To update the `.pot` file when strings in the app change:

- Open a "Build terminal" in Builder from the + menu in the top left
- Run: ninja parolu-pot

To update the individual `.po` files with new strings:

- Open a "Build terminal" in Builder from the + menu in the top left
- Run: ninja parolu-update-po

## Updating dependencies

Dependencies are in `requirements.txt`, which is the source of truth for `pip-dependencies.json`. How to generate:

1. Update `requirements.txt`
2. Set up [flatpak-pip-generator](https://github.com/flatpak/flatpak-builder-tools/tree/master/pip) (on GNOME OS this can be done on the host, no toolbox needed):
    - Install dependency `pip3 install --user requirements-parser`
    - Refresh `flatpak-pip-generator.py` in the repo from upstream if needed.
3. Run `python3 flatpak-pip-generator.py --runtime='org.gnome.Sdk//51' --requirements-file='requirements.txt' --output pypi-dependencies`
4. Manual updates in generated pypi-dependencies.json:
   - add onnxruntime by hand, as cp314-cp314 manylinux wheels for x86_64 and aarch64 (not cp314t), each with only-arches.
   - piper-tts source tarball is unusable (no espeak-ng data), so replace it with the abi3 wheels the same way.
   - re-add "cleanup": ["*"] to python3-meson-python and python3-scikit-build, since both are only needed during the build.
5. Update the contents of pip-dependencies.json with the new dependencies and delete the temporary pypi-dependencies.json.

## Testing languages

In GNOME Builder, open a new runtime terminal and try languages with:

```
LANGUAGE=es_MX parolu
```
