import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QSpinBox, QMessageBox
)

class MatrixTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matrix Operations Tool (PyQt)")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Controls for matrix size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Rows:"))
        self.rows_input = QSpinBox()
        self.rows_input.setRange(1, 20)
        self.rows_input.setValue(2)
        size_layout.addWidget(self.rows_input)

        size_layout.addWidget(QLabel("Columns:"))
        self.cols_input = QSpinBox()
        self.cols_input.setRange(1, 20)
        self.cols_input.setValue(2)
        size_layout.addWidget(self.cols_input)

        self.layout.addLayout(size_layout)

        # Matrices
        self.matrixA = QTableWidget(2, 2)
        self.matrixB = QTableWidget(2, 2)
        self.resultMatrix = QTableWidget()

        self.layout.addWidget(QLabel("Matrix A"))
        self.layout.addWidget(self.matrixA)
        self.layout.addWidget(QLabel("Matrix B"))
        self.layout.addWidget(self.matrixB)
        self.layout.addWidget(QLabel("Result"))
        self.layout.addWidget(self.resultMatrix)

        # Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.sub_btn = QPushButton("Subtract")
        self.mul_btn = QPushButton("Multiply")
        self.trans_btn = QPushButton("Transpose A")
        self.det_btn = QPushButton("Determinant A")

        for btn in [self.add_btn, self.sub_btn, self.mul_btn, self.trans_btn, self.det_btn]:
            btn_layout.addWidget(btn)

        self.layout.addLayout(btn_layout)

        # Connect buttons
        self.add_btn.clicked.connect(self.add_matrices)
        self.sub_btn.clicked.connect(self.subtract_matrices)
        self.mul_btn.clicked.connect(self.multiply_matrices)
        self.trans_btn.clicked.connect(self.transpose_matrix)
        self.det_btn.clicked.connect(self.determinant_matrix)

        # Update matrices when size changes
        self.rows_input.valueChanged.connect(self.update_matrix_size)
        self.cols_input.valueChanged.connect(self.update_matrix_size)

    def update_matrix_size(self):
        rows = self.rows_input.value()
        cols = self.cols_input.value()
        self.matrixA.setRowCount(rows)
        self.matrixA.setColumnCount(cols)
        self.matrixB.setRowCount(rows)
        self.matrixB.setColumnCount(cols)

    def read_matrix(self, table):
        rows = table.rowCount()
        cols = table.columnCount()
        mat = np.zeros((rows, cols))
        try:
            for i in range(rows):
                for j in range(cols):
                    value = table.item(i, j)
                    mat[i,j] = float(value.text()) if value else 0.0
            return mat
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers in all cells.")
            return None

    def display_result(self, mat):
        rows, cols = mat.shape
        self.resultMatrix.setRowCount(rows)
        self.resultMatrix.setColumnCount(cols)
        for i in range(rows):
            for j in range(cols):
                self.resultMatrix.setItem(i, j, QTableWidgetItem(f"{mat[i,j]:.2f}"))

    def add_matrices(self):
        A = self.read_matrix(self.matrixA)
        B = self.read_matrix(self.matrixB)
        if A is None or B is None: return
        if A.shape != B.shape:
            QMessageBox.warning(self, "Error", "Matrices must have the same shape for addition.")
            return
        self.display_result(A + B)

    def subtract_matrices(self):
        A = self.read_matrix(self.matrixA)
        B = self.read_matrix(self.matrixB)
        if A is None or B is None: return
        if A.shape != B.shape:
            QMessageBox.warning(self, "Error", "Matrices must have the same shape for subtraction.")
            return
        self.display_result(A - B)

    def multiply_matrices(self):
        A = self.read_matrix(self.matrixA)
        B = self.read_matrix(self.matrixB)
        if A is None or B is None: return
        if A.shape[1] != B.shape[0]:
            QMessageBox.warning(self, "Error", "Columns of A must equal rows of B for multiplication.")
            return
        self.display_result(A @ B)

    def transpose_matrix(self):
        A = self.read_matrix(self.matrixA)
        if A is None: return
        self.display_result(A.T)

    def determinant_matrix(self):
        A = self.read_matrix(self.matrixA)
        if A is None: return
        if A.shape[0] != A.shape[1]:
            QMessageBox.warning(self, "Error", "Matrix must be square to calculate determinant.")
            return
        det = np.linalg.det(A)
        QMessageBox.information(self, "Determinant", f"Determinant of Matrix A: {det:.4f}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MatrixTool()
    window.show()
    sys.exit(app.exec_())
