import os

import cv2
import open3d.visualization.gui as gui # type: ignore

from .constants import DEFAULT_ZOOM, MIN_ZOOM, MAX_ZOOM
from .display import DisplayMixin
from .file_io import FileIOMixin
from .interaction import AnnotationMixin
from .navigation import NavigationMixin


class ManualFeatureAnnotator(FileIOMixin, AnnotationMixin, NavigationMixin, DisplayMixin):
    def __init__(self, image_folder, output_dir="colmap_manual"):
        self.image_folder = image_folder
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.image_files = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.jpg', '.png', '.jpeg'))
        ])
        if len(self.image_files) < 2:
            print("Error: at least two pictures")

        self.current_idx = 0

        self.annotations = {f: {} for f in self.image_files}
        self.image_metadata = {f: None for f in self.image_files}
        self.max_point3d_id = 0

        self.sift = cv2.SIFT_create() # type: ignore

        self.current_feature_id = 1
        self.zoom_factor = DEFAULT_ZOOM

        self.delete_mode = False
        self.drag_start_coord = None
        self.drag_curr_coord = None
        self.drag_is_left = None

        self.app = gui.Application.instance
        self.app.initialize()
        self.window = self.app.create_window("Open3D Manual SfM Annotator", 2000, 1200)

        # key events callback
        self.window.set_on_key(self._on_key)

        self._build_layout()

        self.cv_img_left = None
        self.cv_img_right = None

        if len(self.image_files) >= 2:
            self._load_pair()

    def _build_layout(self):
        self.main_layout = gui.Vert(0, gui.Margins(10, 10, 10, 10))

        controls = gui.Horiz(10)

        self.btn_import = gui.Button("Import images.txt")
        self.btn_import.set_on_clicked(self._on_import_select_file)
        controls.add_child(self.btn_import)

        controls.add_child(gui.Label("Feature ID:"))
        self.id_input = gui.NumberEdit(gui.NumberEdit.INT)
        self.id_input.int_value = self.current_feature_id
        self.id_input.set_on_value_changed(self._on_id_change)
        controls.add_child(self.id_input)

        self.info_label = gui.Label(" Mode: Add Point ")
        self.info_label.text_color = gui.Color(0, 0.8, 0)
        controls.add_child(self.info_label)

        controls.add_child(gui.Label("Zoom (x):"))
        self.zoom_input = gui.NumberEdit(gui.NumberEdit.DOUBLE)
        self.zoom_input.double_value = self.zoom_factor
        self.zoom_input.set_on_value_changed(self._on_zoom_change)
        controls.add_child(self.zoom_input)

        self.btn_undo = gui.Button("Toggle Delete Mode (U)")
        self.btn_undo.set_on_clicked(self._toggle_delete_mode)
        self.btn_undo.background_color = gui.Color(0.6, 0.6, 0.6)
        controls.add_child(self.btn_undo)

        self.btn_delete_single = gui.Button("Del Single (D)")
        self.btn_delete_single.set_on_clicked(lambda: self._on_delete_single())
        controls.add_child(self.btn_delete_single)

        self.btn_prev = gui.Button("Prev Pair (P)")
        self.btn_prev.set_on_clicked(self._on_prev)
        controls.add_child(self.btn_prev)

        self.btn_next = gui.Button("Next Pair (N)")
        self.btn_next.set_on_clicked(self._on_next)
        controls.add_child(self.btn_next)

        self.btn_export_images = gui.Button("Export Corrected images.txt")
        self.btn_export_images.set_on_clicked(self._on_export_images_txt)
        controls.add_child(self.btn_export_images)

        self.main_layout.add_child(controls)

        images_layout = gui.Horiz(10)
        self.left_panel = gui.Vert(5)
        self.left_label = gui.Label("Image Left")
        self.left_widget = gui.ImageWidget()
        self.left_panel.add_child(self.left_label)
        self.left_panel.add_child(self.left_widget)
        self.left_panel.add_stretch()

        self.right_panel = gui.Vert(5)
        self.right_label = gui.Label("Image Right")
        self.right_widget = gui.ImageWidget()
        self.right_panel.add_child(self.right_label)
        self.right_panel.add_child(self.right_widget)
        self.right_panel.add_stretch()

        images_layout.add_child(self.left_panel)
        images_layout.add_stretch()
        images_layout.add_child(self.right_panel)

        self.main_layout.add_child(images_layout)
        self.main_layout.add_stretch()
        self.window.add_child(self.main_layout)

    def _on_id_change(self, new_val):
        self.current_feature_id = int(new_val)
        self.app.post_to_main_thread(self.window, self._update_display_images)

    def _on_zoom_change(self, new_val):
        try:
            zoom_val = float(new_val)
        except Exception:
            zoom_val = self.zoom_factor

        zoom_val = max(MIN_ZOOM, min(MAX_ZOOM, zoom_val))
        self.zoom_factor = zoom_val

        current_val = getattr(self.zoom_input, 'double_value', zoom_val)
        if abs(current_val - zoom_val) > 1e-3:
            self.app.post_to_main_thread(self.window, lambda: setattr(self.zoom_input, 'double_value', zoom_val))

        self.app.post_to_main_thread(self.window, self._update_display_images)

    def _on_key(self, event):
        if event.type == gui.KeyEvent.Type.DOWN:
            if event.key == gui.KeyName.N:
                self._on_next()
                return True
            elif event.key == gui.KeyName.P:
                self._on_prev()
                return True
            elif event.key == gui.KeyName.U:
                self._toggle_delete_mode()
                return True
            elif event.key == gui.KeyName.D:
                self._on_delete_single()
                return True

        return False

    def _toggle_delete_mode(self):
        self.delete_mode = not self.delete_mode
        self.drag_start_coord = None
        self.drag_curr_coord = None

        if self.delete_mode:
            self.info_label.text = " Mode: BOX DELETE (Drag to delete) "
            self.info_label.text_color = gui.Color(1.0, 0, 0)
            self.window.title = "Open3D Manual SfM Annotator - [DELETE MODE]"
        else:
            self.info_label.text = " Mode: Add Point "
            self.info_label.text_color = gui.Color(0, 0.8, 0)
            self.window.title = "Open3D Manual SfM Annotator"

        self.window.set_needs_layout()

    def _show_message(self, title, msg):
        dlg = gui.Dialog(title)
        layout = gui.Vert(10, gui.Margins(10, 10, 10, 10))
        layout.add_child(gui.Label(msg))
        btn = gui.Button("OK")
        btn.set_on_clicked(lambda: self.window.close_dialog())
        layout.add_child(btn)
        dlg.add_child(layout)
        self.window.show_dialog(dlg)

    def run(self):
        self.app.run()
