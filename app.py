import sys, traceback, os
from PyQt6.QtCore import Qt, QSettings, QRunnable, QThreadPool, pyqtSlot, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QCheckBox, QFileDialog, QLabel, QLineEdit, QProgressBar, QPushButton, QGridLayout, QWidget, QComboBox, QVBoxLayout, QHBoxLayout
from PyQt6.QtGui import QPixmap, QIcon
from PIL import Image

basedir = os.path.dirname(__file__)

class WorkerSignals(QObject):
    started = pyqtSignal(bool)
    fileCount = pyqtSignal(int)
    currentFileName = pyqtSignal(str)
    currentImage = pyqtSignal(str)
    updated = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    finished = pyqtSignal(bool)

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        self.kwargs['status_text'] = self.signals.currentFileName
        self.kwargs['num_of_files'] = self.signals.fileCount
        self.kwargs['file_processed'] = self.signals.updated
        self.kwargs['image_to_display'] = self.signals.currentImage
    
    @pyqtSlot()
    def run(self):
        self.signals.started.emit(False)
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.print_exc()))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit(True)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(400)
        self.setMaximumHeight(225)

        FILE_FORMATS = [
        ".png",
        ".jpeg",
        ".gif",
        ".tiff",
        ".tga"    
        ]

        filePathLayout = QGridLayout()
        rawLabel = QLabel("Raw Images Folder")
        self.rawPathField = QLineEdit()
        self.rawPathField.setPlaceholderText("Put the original folder path here")
        editedLabel = QLabel("Edited Images Path")
        self.editedPathField = QLineEdit()
        self.editedPathField.setPlaceholderText("Put the folder path where you want new images")
        self.rawButton = QPushButton("Select")
        self.editedButton = QPushButton("Select")
        self.rawButton.clicked.connect(self.getRawPath)
        self.editedButton.clicked.connect(self.getEditedPath)
        filePathLayout.addWidget(rawLabel, 0, 0)
        filePathLayout.addWidget(self.rawPathField, 1, 0)
        filePathLayout.addWidget(self.rawButton, 1, 1)
        filePathLayout.addWidget(editedLabel, 2, 0)
        filePathLayout.addWidget(self.editedPathField, 3, 0)
        filePathLayout.addWidget(self.editedButton, 3, 1)

        formatLayout = QHBoxLayout()
        fileFormatLabel = QLabel("File format")
        fileFormatLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.fileFormatDropdown = QComboBox()
        self.fileFormatDropdown.addItems(FILE_FORMATS)
        formatLayout.addWidget(fileFormatLabel)
        formatLayout.addWidget(self.fileFormatDropdown)
        
        deleteLayout = QHBoxLayout()
        willDeleteLabel = QLabel("Delete originals")
        willDeleteLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.willDelete = QCheckBox()
        self.willDelete.setChecked(False)
        deleteLayout.addWidget(willDeleteLabel)
        deleteLayout.addWidget(self.willDelete)

        optionsLayout = QHBoxLayout()
        optionsLayout.addLayout(formatLayout)
        optionsLayout.addLayout(deleteLayout)

        contentLayout = QVBoxLayout()
        contentLayout.addLayout(filePathLayout)
        contentLayout.addLayout(optionsLayout)

        self.goButton = QPushButton("Start")
        self.goButton.clicked.connect(self.startProcessingThread)

        self.progressLabel = QLabel("Ready.")
        self.progressLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar = QProgressBar()
        self.progressBar.hide()

        self.imageThumbnail = QLabel()
        self.imageThumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imageThumbnail.hide()
        
        self.layout = QVBoxLayout()
        self.layout.addLayout(contentLayout)
        self.layout.addWidget(self.goButton)
        self.layout.addWidget(self.imageThumbnail)
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.progressLabel)

        self.settings = QSettings("Edenson Games", "BatchImageConverter")

        self.setWindowTitle("Batch Image Converter")
        self.setWindowIcon(QIcon(os.path.join(basedir, "serana.png")))
        widget = QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        try:
            self.rawPathField.setText(self.settings.value("Raw Image Path"))
            self.editedPathField.setText(self.settings.value("Edited Image Path"))
            checked = self.settings.value("Delete Originals", type=bool)
            self.willDelete.setChecked(checked)
            currentFileFormat = self.settings.value("File Format")
            self.fileFormatDropdown.setCurrentText(currentFileFormat)
        except:
            pass

        self.threadpool = QThreadPool()
        #print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        
        # end of main window code

    def startProcessingThread(self):
        worker = Worker(self.convertScreenshots)
        worker.signals.started.connect(self.toggleInteractables)
        worker.signals.started.connect(self.resetProgressBar)
        worker.signals.fileCount.connect(self.collateFilesToProcess)
        worker.signals.currentFileName.connect(self.progressText)
        worker.signals.currentImage.connect(self.enableImagePreview)
        worker.signals.updated.connect(self.updateProgressBar)
        worker.signals.finished.connect(self.toggleInteractables)
        worker.signals.finished.connect(self.finishText)
        worker.signals.finished.connect(self.disableImagePreview)
        self.threadpool.start(worker)

    def closeEvent(self, event):
        self.settings.setValue("Raw Image Path", self.rawPathField.text())
        self.settings.setValue("Edited Image Path", self.editedPathField.text())
        self.settings.setValue("Delete Originals", self.willDelete.isChecked())
        self.settings.setValue("File Format", self.fileFormatDropdown.currentText())

    def getRawPath(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialogSuccessful = dialog.exec()

        if dialogSuccessful:
            selectedFolders = dialog.selectedFiles()
            rawPath = selectedFolders[0]
            self.rawPathField.setText(rawPath)
        else:
            return

    def getEditedPath(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialogSuccessful = dialog.exec()

        if dialogSuccessful:
            selectedFolders = dialog.selectedFiles()
            editedPath = selectedFolders[0]
            self.editedPathField.setText(editedPath)
        else:
            return
        
    def toggleInteractables(self, shouldEnable: bool):
        self.rawButton.setEnabled(shouldEnable)
        self.editedButton.setEnabled(shouldEnable)
        self.goButton.setEnabled(shouldEnable)
        self.rawPathField.setEnabled(shouldEnable)
        self.editedPathField.setEnabled(shouldEnable)
        self.willDelete.setEnabled(shouldEnable)
        self.fileFormatDropdown.setEnabled(shouldEnable)

    def resetProgressBar(self):
        self.progressBar.reset()

    def finishText(self):
        """
        Changes the progress text to be obviously finished. Called by the finished signal.
        """
        self.progressLabel.setText("Finished.")
        self.progressLabel.setStyleSheet(
            'background-color: "green"; color: "white";'
        )

    def progressText(self, text: str):
        """
        Sets the progress text. Called by the progress signal.
        """
        self.progressLabel.setText(text)

    def collateFilesToProcess(self, howMany: int):
        """
        Counts how many files there are to process, and sets the progress bar's maximum to that.
        """
        self.progressBar.show()
        self.progressBar.setMaximum(howMany)

    def updateProgressBar(self):
        """
        Updates the progress bar by 1. Called by the iterating signal, which goes off when a file is processed.
        """
        value = self.progressBar.value()
        if value == -1:
            newValue = value + 2
        else:
            newValue = value + 1
        self.progressBar.setValue(newValue)
        print(f"On pass {newValue}")

    def enableImagePreview(self, imageToDisplay: str):
        self.imageThumbnail.show()
        self.setMaximumHeight(self.height() + 400)
        newPixmap = QPixmap(imageToDisplay).scaled(400, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        self.imageThumbnail.setMaximumSize(400, 400)
        self.imageThumbnail.setPixmap(newPixmap)

    def disableImagePreview(self):
        self.imageThumbnail.hide()
        self.setMaximumHeight(225)
        self.imageThumbnail.setMaximumSize(0, 0)
        self.imageThumbnail.clear()
    
    def convertScreenshots(self, status_text, num_of_files, file_processed, image_to_display):
        rawPath = self.rawPathField.text()
        editedPath = self.editedPathField.text()
        rawFiles = []
        existingFiles = []
        
        if (rawPath != "") & (editedPath != ""):
            os.chdir(editedPath)
            for file in os.listdir(editedPath):
                existingFiles.append(file)
                
            os.chdir(rawPath)
            for file in os.listdir(rawPath):
                rawFiles.append(file)

            # put signal here
            i = len(rawFiles)
            print(i)
            num_of_files.emit(i)

            for file in rawFiles:
                ending = file[-4:]
                match ending:
                    case "jpeg":
                        ending = ".jpeg"
                    case "tiff":
                        ending = ".tiff"
                    case ".png":
                        pass
                    case ".jpg":
                        pass
                    case ".gif":
                        pass
                    case ".bmp":
                        pass
                    case ".tga":
                        pass
                    case _:
                        continue
                rawFilename = file.strip(ending)
                fileFormat = self.fileFormatDropdown.currentText()
                newFilename = f"{rawFilename}{fileFormat}"

                if newFilename not in existingFiles:
                    status_text.emit(f"Editing {file} now...")
                    image_to_display.emit(file)
                    img = Image.open(file)
                    img.save(f"{editedPath}/{newFilename}")
                    status_text.emit(f"Saved as {newFilename}...")
                    file_processed.emit()
                    img.close()
                else:
                    pass
                
                checked = self.willDelete.isChecked()
                if (checked == True):
                    os.remove(file)

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec()