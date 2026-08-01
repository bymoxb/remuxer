desktop_conf = configuration_data()
desktop_conf.set('ICON', application_id)



# Install desktop file
desktop_file = i18n.merge_file(
        input: configure_file(
                  input: 'dev.illapa.Remuxer.desktop.in',
                 output: '@0@.desktop.in'.format(application_id),
          configuration: desktop_conf,
        ),
       output: '@0@.desktop'.format(application_id),
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif



# Install the metainfo file
metainfo_conf = configuration_data()
metainfo_conf.set('APPID', application_id)
metainfo_conf.set('NAME', project_name)

appstream_file = i18n.merge_file(
        input: configure_file(
                  input: 'dev.illapa.Remuxer.metainfo.xml.in',
                 output: '@0@.metainfo.xml.in'.format(application_id),
          configuration: metainfo_conf,
        ),
       output: '@0@.metainfo.xml'.format(application_id),
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])



# Installing the schema file
gschema_conf = configuration_data()
gschema_conf.set('APP_ID', application_id)

gschema = configure_file(
  input: 'dev.illapa.Remuxer.gschema.xml.in',
  output: '@0@.gschema.xml'.format(application_id),
  configuration: gschema_conf,
)

install_data(
  gschema,
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])



#
service_conf = configuration_data()
service_conf.set('APP_ID', application_id)
service_conf.set('bindir', get_option('prefix') / get_option('bindir'))
configure_file(
  input: 'dev.illapa.Remuxer.service.in',
  output: '@0@.service'.format(application_id),
  configuration: service_conf,
  install_dir: get_option('datadir') / 'dbus-1' / 'services'
)

subdir('icons')
