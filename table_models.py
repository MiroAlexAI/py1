from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QColor

class ResultsTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self._headers = ["Select", "Slot", "Model", "Response", "Symbols", "Metrics & Status", "Preview"]
        self.active_model_names = set() # Имена моделей, которые нужно подсветить

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        item = self._data[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == 1: return item.get('slot', 'P1')
            if col == 2: return item['model']
            if col == 3: 
                resp = item['response']
                lines = resp.split('\n')
                if len(lines) > 3:
                    return "\n".join(lines[:3]) + "..."
                return (resp[:200] + '...') if len(resp) > 200 else resp
            if col == 4: return str(len(item['response']))
            if col == 5: 
                status = item['status']
                t = item.get('resp_time', 0)
                metrics = item.get('metrics', {})
                avg = metrics.get('avg_time', 0)
                errs = metrics.get('errors', 0)
                
                info = f"[{status}]"
                if t > 0: info += f" {t:.1f}s"
                if avg > 0 or errs > 0:
                    info += f" (Avg:{avg}s | Err:{errs})"
                return info
            if col == 6: return "🔍 Open"
        
        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            return Qt.CheckState.Checked if item.get('selected') else Qt.CheckState.Unchecked

        # Подсветка фона для активных моделей
        if role == Qt.ItemDataRole.BackgroundRole:
            if item['model'] in self.active_model_names:
                return QColor("#e3f2fd") # Нежно-голубой для активных

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid(): return False
        
        row = index.row()
        col = index.column()

        if role == Qt.ItemDataRole.CheckStateRole and col == 0:
            if isinstance(value, int):
                checked = (value == Qt.CheckState.Checked.value)
            else:
                checked = (value == Qt.CheckState.Checked)
            self._data[row]['selected'] = checked
            self.dataChanged.emit(index, index, [role])
            return True
        
        if role == Qt.ItemDataRole.EditRole and col == 3:
            self._data[row]['response'] = value
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])
            return True
            
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        for item in self._data:
            if 'selected' not in item:
                item['selected'] = False
        self.endResetModel()

    def set_active_models(self, model_names):
        """Обновление списка имен моделей для подсветки."""
        self.active_model_names = set(model_names)
        self.layoutChanged.emit()
