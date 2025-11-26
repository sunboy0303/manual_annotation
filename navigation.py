import os

import cv2


class NavigationMixin:
    """Image pair traversal and loading helpers."""

    def _on_next(self):
        if self.current_idx >= len(self.image_files) - 2:
            self._show_message("Info", "No more images.")
            return

        new_left_name = self.image_files[self.current_idx + 1]
        if self.current_idx + 2 < len(self.image_files):
            new_right_name = self.image_files[self.current_idx + 2]
        else:
            new_right_name = None

        ids_on_new_left = set(self.annotations[new_left_name].keys())
        ids_on_new_right = set(self.annotations[new_right_name].keys()) if new_right_name and new_right_name in self.annotations else set()

        if ids_on_new_left:
            missing_ids = sorted(list(ids_on_new_left - ids_on_new_right))
            if missing_ids:
                self.current_feature_id = missing_ids[0]
            else:
                self.current_feature_id = max(ids_on_new_left) + 1
        else:
            self.current_feature_id = 1

        self.current_idx += 1
        self.app.post_to_main_thread(self.window, lambda: setattr(self.id_input, 'int_value', self.current_feature_id))
        self.app.post_to_main_thread(self.window, self._load_pair)

    def _on_prev(self):
        if self.current_idx <= 0:
            self._show_message("Info", "Already at the first image pair.")
            return

        self.current_idx -= 1
        print(f"Switched back to pair {self.current_idx} & {self.current_idx+1}.")

        self.app.post_to_main_thread(self.window, self._load_pair)

    def _load_pair(self):
        if self.current_idx >= len(self.image_files) - 1:
            self.app.post_to_main_thread(self.window, lambda: setattr(self.left_label, 'text', "End of Images"))
            self.app.post_to_main_thread(self.window, lambda: setattr(self.right_label, 'text', ""))
            return

        name_left = self.image_files[self.current_idx]
        name_right = self.image_files[self.current_idx + 1]

        path_left = os.path.join(self.image_folder, name_left)
        path_right = os.path.join(self.image_folder, name_right)

        self.cv_img_left = cv2.imread(path_left)
        self.cv_img_right = cv2.imread(path_right)

        if self.cv_img_left is None or self.cv_img_right is None:
            print(f"Error loading images: {name_left} or {name_right}")
            return

        self.app.post_to_main_thread(self.window, lambda: self._set_pair_labels(name_left, name_right))
        self.app.post_to_main_thread(self.window, self._update_display_images)

    def _set_pair_labels(self, name_left, name_right):
        self.left_label.text = f"Left: {name_left} (Index {self.current_idx})"
        self.right_label.text = f"Right: {name_right} (Index {self.current_idx + 1})"
