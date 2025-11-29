import cv2
import open3d.visualization.gui as gui

from .constants import DEFAULT_SCALE


class AnnotationMixin:
    """Feature add/delete operations and mouse interactions."""

    def _on_delete_single(self):
        current_id = self.current_feature_id
        name_left = self.image_files[self.current_idx]
        name_right = self.image_files[self.current_idx + 1]

        deleted = False
        if current_id in self.annotations[name_left]:
            del self.annotations[name_left][current_id]
            deleted = True
        if current_id in self.annotations[name_right]:
            del self.annotations[name_right][current_id]
            deleted = True

        if deleted:
            self.app.post_to_main_thread(self.window, self._update_display_images)
        else:
            print(f"ID {current_id} not found to delete.")

    def _add_feature_point(self, is_left, x, y):
        target_img = self.cv_img_left if is_left else self.cv_img_right
        filename = self.image_files[self.current_idx if is_left else self.current_idx + 1]

        current_id = self.current_feature_id
        point3d_id = -1

        if current_id in self.annotations[filename]:
            point3d_id = self.annotations[filename][current_id][5]
        elif is_left:
            self.max_point3d_id += 1
            point3d_id = self.max_point3d_id
        elif not is_left and current_id in self.annotations[self.image_files[self.current_idx]]:
            point3d_id = self.annotations[self.image_files[self.current_idx]][current_id][5]

        kp = cv2.KeyPoint(float(x), float(y), DEFAULT_SCALE)
        gray = cv2.cvtColor(target_img, cv2.COLOR_BGR2GRAY) if len(target_img.shape) == 3 else target_img
        kps, des = self.sift.compute(gray, [kp])

        if des is not None and len(des) > 0:
            self.annotations[filename][current_id] = (
                x, y, des[0], kps[0].size, kps[0].angle, point3d_id
            )
            print(f"Marked/Updated ID {current_id} ({'Left' if is_left else 'Right'}). 3D ID: {point3d_id} ({x:.2f}, {y:.2f})")

            name_left = self.image_files[self.current_idx]
            name_right = self.image_files[self.current_idx + 1]
            has_left = current_id in self.annotations[name_left]
            has_right = current_id in self.annotations[name_right]

            if has_left and has_right:
                print(f"Feature {current_id} complete. Auto-incrementing...")
                self.current_feature_id += 1
                self.app.post_to_main_thread(self.window, lambda: setattr(self.id_input, 'int_value', self.current_feature_id))
        else:
            print(f"Warning: Could not compute SIFT descriptor at ({x:.2f}, {y:.2f}) on {filename}. Point not saved.")

    def _delete_points_in_box(self, is_left, x1, y1, x2, y2):
        filename = self.image_files[self.current_idx if is_left else self.current_idx + 1]

        x_min, x_max = min(x1, x2), max(x1, x2)
        y_min, y_max = min(y1, y2), max(y1, y2)

        ids_to_delete = []
        for fid, data in self.annotations[filename].items():
            fx, fy = data[0], data[1]
            if x_min <= fx <= x_max and y_min <= fy <= y_max:
                ids_to_delete.append(fid)

        for fid in ids_to_delete:
            del self.annotations[filename][fid]

        print(f"Box Delete: Removed {len(ids_to_delete)} points from {filename}")

    def _on_mouse_event(self, event, is_left):
        if event.type == gui.MouseEvent.Type.BUTTON_DOWN and event.is_button_down(gui.MouseButton.LEFT):
            widget = self.left_widget if is_left else self.right_widget
            coords = self._get_img_coords_from_mouse(widget, event.x, event.y, is_left)

            if coords:
                img_x, img_y = coords
                img_orig = self.cv_img_left if is_left else self.cv_img_right
                h, w = img_orig.shape[:2]

                if -0.01 <= img_x <= w and -0.01 <= img_y <= h:
                    if self.delete_mode:
                        self.drag_start_coord = (img_x, img_y)
                        self.drag_curr_coord = (img_x, img_y)
                        self.drag_is_left = is_left
                        self.app.post_to_main_thread(self.window, self._update_display_images)
                    else:
                        self._add_feature_point(is_left, img_x, img_y)
                        self.app.post_to_main_thread(self.window, self._update_display_images)

            return True

        elif event.type == gui.MouseEvent.Type.DRAG:
            if self.delete_mode and self.drag_start_coord is not None:
                if is_left == self.drag_is_left:
                    widget = self.left_widget if is_left else self.right_widget
                    coords = self._get_img_coords_from_mouse(widget, event.x, event.y, is_left)
                    if coords:
                        self.drag_curr_coord = coords
                        self.app.post_to_main_thread(self.window, self._update_display_images)
                return True

        elif event.type == gui.MouseEvent.Type.BUTTON_UP:
            if self.delete_mode and self.drag_start_coord is not None:
                if is_left == self.drag_is_left:
                    x1, y1 = self.drag_start_coord
                    x2, y2 = self.drag_curr_coord if self.drag_curr_coord else (x1, y1)

                    self._delete_points_in_box(is_left, x1, y1, x2, y2)

                self.drag_start_coord = None
                self.drag_curr_coord = None
                self.drag_is_left = None
                self.app.post_to_main_thread(self.window, self._update_display_images)
                return True

        return False
