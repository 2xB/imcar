from PyQt5 import QtWidgets
import numpy as np
import os
import unicodedata
import re

# License comment regarding the following function "slugify" (BSD-3):
# From the Django Framework as presented by S. Lott and Wernight in https://stackoverflow.com/a/295466
# The following code is licensed under the following terms:

# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.
# 
#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.
# 
#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = str(re.sub(r'[^\w\s-]', '', value).strip().lower())
    value = str(re.sub(r'[-\s]+', '-', value))
    return value

# ---

dlg = None

def snapshot_save_dialog(snapshot, title='Save Snapshot'):
    global dlg # Prevent garbage collection
    """
    Shows nonmodal save dialog.

    Requires existing QApplication.
    """
    dlg = QtWidgets.QFileDialog()
    dlg.setWindowTitle(title)
    dlg.setViewMode(QtWidgets.QFileDialog.Detail)
    dlg.setNameFilters( [dlg.tr('CSV file; Separator: Semicolon (*.csv)'), dlg.tr('All Files (*)')] )
    dlg.setDefaultSuffix( '.csv' )
    dlg.setFileMode(QtWidgets.QFileDialog.AnyFile);
    dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
    
    def savefile(self):
        filename = dlg.selectedFiles()[0]
        snapshot.save(filename)
    dlg.fileSelected.connect(savefile)

    dlg.show()
    
    return dlg

def snapshots_save_dialog(snapshots, title='Save all Snapshots'):
    global dlg # Prevent garbage collection
    """
    Shows nonmodal save dialog.

    Requires existing QApplication.
    """
    dlg = QtWidgets.QFileDialog()
    dlg.setWindowTitle(title)
    dlg.setViewMode(QtWidgets.QFileDialog.Detail)
    dlg.setNameFilters( [dlg.tr('CSV file; Separator: Semicolon (*.csv)'), dlg.tr('All Files (*)')] )
    dlg.setFileMode(QtWidgets.QFileDialog.Directory);
    dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
    dlg.setOption(QtWidgets.QFileDialog.ShowDirsOnly)
    dlg.setOption(QtWidgets.QFileDialog.DontConfirmOverwrite)
    
    def savefile(self):
        path = dlg.selectedUrls()[0].toLocalFile()
        for snapshot in snapshots:
            filename = os.path.join(path, slugify(snapshot.get_name()) + ".csv")
            snapshot.save(filename)
    dlg.fileSelected.connect(savefile)

    dlg.show()
    
    return dlg
