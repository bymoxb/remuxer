project('remuxer',
          version: '0.1.0',
    meson_version: '>= 1.0.0',
          license: 'GPL-3.0-only',
)

i18n = import('i18n')
gnome = import('gnome')

project_id = 'dev.illapa.Remuxer'
project_name = 'Remuxer'
app_github = 'https://github.com/bymoxb/remuxer'
app_github_api = 'https://api.github.com/repos/bymoxb/remuxer/releases/latest'

# Profiles
application_id = project_id
if get_option('profile') == 'development'
  profile = 'Devel'
else
  profile = ''
endif

subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)
