pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'remuxer'
gnome = import('gnome')

gnome.compile_resources('remuxer',
  'remuxer.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'remuxer.in',
  output: 'remuxer',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

remuxer_sources = [
  '__init__.py',
  'main.py',
  'window.py',
]

install_data(remuxer_sources, install_dir: moduledir)

install_subdir(
  'models',
  install_dir: moduledir,
)

install_subdir(
  'services',
  install_dir: moduledir,
)
