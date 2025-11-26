import cv2
import open3d as o3d


class DisplayMixin:
    """Rendering helpers for showing images and mapping coordinates."""

    def _update_display_images(self):
        if self.cv_img_left is None or self.cv_img_right is None:
            return

        name_left = self.image_files[self.current_idx]
        name_right = self.image_files[self.current_idx + 1]

        vis_left_orig = self.cv_img_left.copy()
        vis_right_orig = self.cv_img_right.copy()

        h, w = vis_left_orig.shape[:2]
        current_zoom = self.zoom_factor

        if current_zoom != 1.0:
            new_size = (int(w * current_zoom), int(h * current_zoom))
            vis_left_disp = cv2.resize(vis_left_orig, new_size, interpolation=cv2.INTER_NEAREST)
            vis_right_disp = cv2.resize(vis_right_orig, new_size, interpolation=cv2.INTER_NEAREST)
        else:
            vis_left_disp = vis_left_orig
            vis_right_disp = vis_right_orig

        def draw_points(img, filename, current_id):
            for fid, data in self.annotations[filename].items():
                x, y, _, _, _, point3d_id = data

                draw_x = int(x * current_zoom)
                draw_y = int(y * current_zoom)

                if fid == current_id:
                    color = (0, 255, 0)
                    thickness = 2
                    radius = 6
                elif point3d_id > 0:
                    color = (255, 0, 0)
                    thickness = 1
                    radius = 4
                else:
                    color = (0, 0, 255)
                    thickness = 1
                    radius = 4

                cv2.circle(img, (draw_x, draw_y), radius, color, thickness)
                cv2.putText(img, str(fid), (draw_x + 5, draw_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        draw_points(vis_left_disp, name_left, self.current_feature_id)
        draw_points(vis_right_disp, name_right, self.current_feature_id)

        if self.delete_mode and self.drag_start_coord is not None and self.drag_curr_coord is not None:
            target_vis = vis_left_disp if self.drag_is_left else vis_right_disp

            x1 = int(self.drag_start_coord[0] * current_zoom)
            y1 = int(self.drag_start_coord[1] * current_zoom)
            x2 = int(self.drag_curr_coord[0] * current_zoom)
            y2 = int(self.drag_curr_coord[1] * current_zoom)

            cv2.rectangle(target_vis, (x1, y1), (x2, y2), (0, 0, 255), 2)

        self._set_o3d_image(self.left_widget, vis_left_disp)
        self._set_o3d_image(self.right_widget, vis_right_disp)

        self.left_widget.set_on_mouse(lambda e: self._on_mouse_event(e, is_left=True))
        self.right_widget.set_on_mouse(lambda e: self._on_mouse_event(e, is_left=False))

        self.window.set_needs_layout()

    def _set_o3d_image(self, widget, cv_img):
        img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        o3d_img = o3d.geometry.Image(img_rgb)
        widget.update_image(o3d_img)

    def _get_img_coords_from_mouse(self, widget, event_x, event_y, is_left):
        img_orig = self.cv_img_left if is_left else self.cv_img_right
        if img_orig is None:
            return None

        widget_frame = widget.frame
        current_zoom = self.zoom_factor
        orig_h, orig_w = img_orig.shape[:2]

        displayed_w_pixels = int(orig_w * current_zoom)
        displayed_h_pixels = int(orig_h * current_zoom)

        click_x = event_x - widget_frame.x
        click_y = event_y - widget_frame.y

        allocated_w, allocated_h = widget_frame.width, widget_frame.height
        img_aspect = displayed_w_pixels / displayed_h_pixels
        allocated_aspect = allocated_w / allocated_h

        widget_scale = 1.0
        offset_x = 0
        offset_y = 0

        if img_aspect > allocated_aspect:
            widget_scale = allocated_w / displayed_w_pixels
            visible_h = displayed_h_pixels * widget_scale
            offset_y = (allocated_h - visible_h) / 2
        else:
            widget_scale = allocated_h / displayed_h_pixels
            visible_w = displayed_w_pixels * widget_scale
            offset_x = (allocated_w - visible_w) / 2

        x_in_zoomed_img = (click_x - offset_x) / widget_scale
        y_in_zoomed_img = (click_y - offset_y) / widget_scale

        img_x = x_in_zoomed_img / current_zoom
        img_y = y_in_zoomed_img / current_zoom

        img_x = round(img_x, 2)
        img_y = round(img_y, 2)

        return img_x, img_y
