#!/bin/bash

# Configuration
APP_NAME="remuxer"
PO_DIR="po"
LOCALE_DIR="locale"
UI_DIR="ui"

echo "1. 🛠️  Compiling Blueprint..."
# Compiles the Blueprint file into a GTK .ui XML file
blueprint-compiler compile ${UI_DIR}/main.blp --output ${UI_DIR}/main.ui

echo "2. 📂 Extracting translatable strings..."
# Extract strings from Python source code
xgettext --from-code=UTF-8 --keyword=_ -o ${PO_DIR}/${APP_NAME}.pot main.py
# Append strings from the generated UI file (GTK Builder XML)
xgettext --join-existing --language=Glade --keyword=translatable -o ${PO_DIR}/${APP_NAME}.pot ${UI_DIR}/main.ui

echo "3. 🔄 Updating translation files (.po)..."
# Loop through all available .po files in the po/ directory
for po_file in ${PO_DIR}/*.po; do
    if [ -f "$po_file" ]; then
        echo "   -> Updating $po_file"
        # msgmerge merges the new template (.pot) with existing translations (.po)
        # It keeps existing translations and adds new ones
        msgmerge --update --backup=none "$po_file" ${PO_DIR}/${APP_NAME}.pot
    fi
done

echo "4. 📦 Compiling binary catalogs (.mo)..."
# Convert human-readable .po files into binary .mo files for the application
for po_file in ${PO_DIR}/*.po; do
    if [ -f "$po_file" ]; then
        # Extract the language code (e.g., 'es', 'fr') from the filename
        lang=$(basename "$po_file" .po)
        dest_dir="${LOCALE_DIR}/${lang}/LC_MESSAGES"
        
        # Ensure the destination directory exists
        mkdir -p "$dest_dir"
        
        # Compile to binary format
        msgfmt "$po_file" -o "${dest_dir}/${APP_NAME}.mo"
        echo "   -> Generated: ${dest_dir}/${APP_NAME}.mo"
    fi
done

echo "✅ Success! Assets and translations are up to date."
echo "You can now edit your .po files using Poedit or any text editor."
