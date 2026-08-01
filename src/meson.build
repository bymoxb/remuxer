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

const_conf = configuration_data()

const_conf.set('APP_NAME', project_name)
const_conf.set('APP_ID', project_id)
const_conf.set('VERSION', meson.project_version())
const_conf.set('APP_GITHUB', app_github)
const_conf.set('APP_GITHUB_RELEASES', app_github_api)
const_conf.set('PROFILE', profile)

const_py = configure_file(
  input: 'const.py.in',
  output: 'const.py',
  configuration: const_conf
)


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
  const_py,
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
