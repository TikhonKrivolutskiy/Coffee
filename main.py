import os
import sys
import sqlite3
import mainUI, addEditCoffeeFormUI
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox, QWidget


class DbBasicFunctions(object):
    def create_cursor(self):
        self.cur = self.db.cursor()

    def execute_query(self, query):
        return self.cur.execute(query)

    def execute_query_fetchone(self, query):
        return self.cur.execute(query).fetchone()

    def execute_query_fetchall(self, query):
        return self.cur.execute(query).fetchall()

    def close_cursor(self):
        self.cur.close()

    def get_col_names(self):
        self.create_cursor()
        self.execute_query_fetchone("SELECT * FROM coffee")
        names = map(lambda val: val[0], self.cur.description)
        self.close_cursor()
        return tuple(names)

    def commit_changes(self):
        self.db.commit()


class MainWindow(QMainWindow, mainUI.Ui_MainWindow, DbBasicFunctions):
    def __init__(self):
        super().__init__()
        if os.path.isfile("./data/coffee.sqlite"):
            self.db = sqlite3.connect("./data/coffee.sqlite")
        else:
            self.show_messagebox("База данных не найдена")
            sys.exit()
        self.add_edit_form = AddEditCoffeeForm(self, self.db)
        self.initUi()
        self.update_table()

    def initUi(self):
        self.setupUi(self)
        self.retranslateUi(self)
        self.action_exit.triggered.connect(exit)
        self.pushButton_update.clicked.connect(self.update_table)
        self.pushButton_add.clicked.connect(self.open_add_form)
        self.pushButton_edit.clicked.connect(self.open_edit_form)

    def clear_table(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)

    def show_messagebox(self, message):
        msgbox = QMessageBox(self)
        msgbox.setText(message)
        msgbox.show()

    def fill_table(self, header, data):
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setColumnCount(len(header))
        self.tableWidget.setHorizontalHeaderLabels(header)
        self.tableWidget.setRowCount(0)
        for row_num, row_data in enumerate(data):
            self.tableWidget.setRowCount(self.tableWidget.rowCount() + 1)
            for el_num, el in enumerate(row_data):
                item = QTableWidgetItem(str(el))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.tableWidget.setItem(row_num, el_num, item)
        self.tableWidget.hideColumn(0)
        self.tableWidget.setColumnWidth(1, 152)
        self.tableWidget.setColumnWidth(2, 153)
        self.tableWidget.setColumnWidth(3, 153)
        self.tableWidget.setColumnWidth(4, 153)
        self.tableWidget.setColumnWidth(5, 152)

    def update_table(self):
        header = self.get_col_names()
        self.create_cursor()
        data = list(self.execute_query(f"SELECT * FROM coffee"))
        data = [list(row) for row in data]
        replacements = {"type": "types", "taste": "tastes"}
        for row in data:
            for repl_el, repl_tab in replacements.items():
                row_id = header.index(repl_el)
                repl_id = row[row_id]
                new_el = self.execute_query_fetchone(f"SELECT {repl_el} FROM {repl_tab} WHERE id='{repl_id}'")
                if new_el is not None:
                    row[row_id] = new_el[0]
        self.fill_table(header, data)
        self.close_cursor()

    def closeEvent(self, event):
        sys.exit()

    def open_edit_form(self):
        rows = list(set([i.row() for i in self.tableWidget.selectedItems()]))
        if not rows:
            return
        coffee_id = min(self.tableWidget.item(i, 0).text() for i in rows)
        self.add_edit_form.prepare_ui(coffee_id)
        self.add_edit_form.show()

    def open_add_form(self):
        self.add_edit_form.prepare_ui()
        self.add_edit_form.show()


class AddEditCoffeeForm(QWidget, addEditCoffeeFormUI.Ui_Form, DbBasicFunctions):
    def __init__(self, main_form, db):
        super().__init__()
        self.main_form = main_form
        self.db = db
        self.initUi()

    def initUi(self):
        self.setupUi(self)
        self.retranslateUi(self)
        self.pushButton_save.clicked.connect(self.save)
        self.pushButton_cancel.clicked.connect(self.hide)

    def save(self):
        if not self.lineEdit_name.text():
            return
        query_args = []
        query_vals = []
        coffee_id = self.lineEdit_id.text()
        query_vals += [self.lineEdit_name.text(),
                       self.comboBox_type.currentIndex() + 1,
                       self.spinBox_price.value(),
                       self.spinBox_pack_size.value()]
        query_args += ["name", "type", "price", "pack_size"]
        taste = self.lineEdit_taste.text()
        if taste:
            self.create_cursor()
            self.execute_query(f"INSERT INTO tastes (taste) VALUES ('{taste}')")
            taste_id = self.execute_query_fetchone(f"SELECT id FROM tastes WHERE taste='{taste}'")[0]
            self.close_cursor()
            self.commit_changes()
            query_args.append("taste")
            query_vals.append(taste_id)
        self.create_cursor()
        if coffee_id == "AUTO":
            self.execute_query(f"INSERT INTO coffee {tuple(query_args)} VALUES {tuple(query_vals)}")
        else:
            self.execute_query(f"""UPDATE coffee SET {", ".join(map(lambda el: " = ".join(map(lambda e: f"'{e}'", el)), zip(query_args, query_vals)))} WHERE id = {coffee_id}""")
        self.close_cursor()
        self.commit_changes()
        self.fix_taste_table()
        self.hide()
        self.main_form.update_table()

    def fix_taste_table(self):
        self.create_cursor()
        self.execute_query_fetchall("""DELETE FROM tastes WHERE id NOT IN (SELECT taste FROM coffee WHERE taste IS NOT NULL)""")
        self.close_cursor()
        self.commit_changes()

    def edit_coffee(self, coffee_id):
        self.lineEdit_id.setText(str(coffee_id))
        self.show()

    def prepare_ui(self, coffee_id=None):
        self.comboBox_type.clear()
        self.create_cursor()
        types = tuple(el[0] for el in self.execute_query_fetchall(f"SELECT type FROM types"))
        self.comboBox_type.addItems(types)
        if coffee_id is None:
            self.lineEdit_id.setText("AUTO")
            self.lineEdit_name.clear()
            self.lineEdit_taste.clear()
        else:
            _, name, type_id, taste_id, price, pack_size = self.execute_query_fetchone(f"SELECT * FROM coffee WHERE id={coffee_id}")
            coffee_type = self.execute_query_fetchall(f"SELECT type FROM types WHERE id={type_id}")
            if taste_id is not None:
                taste = self.execute_query_fetchone(f"SELECT taste FROM tastes WHERE id={taste_id}")[0]
            else:
                taste = ""
            self.lineEdit_id.setText(str(coffee_id))
            self.lineEdit_name.setText(name)
            self.comboBox_type.setCurrentIndex(type_id - 1)
            self.lineEdit_taste.setText(taste)
            self.spinBox_price.setValue(price)
            self.spinBox_pack_size.setValue(pack_size)
        self.close_cursor()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()