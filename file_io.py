import os

import open3d.visualization.gui as gui

from .constants import DEFAULT_DESCRIPTOR, DEFAULT_SCALE, DEFAULT_ANGLE


class FileIOMixin:
    """Import/export helpers for COLMAP images.txt files."""

    def _on_import_select_file(self):
        def on_dialog_done(path):
            self.window.close_dialog()
            if path:
                self.app.post_to_main_thread(self.window, lambda: self._on_import_images_txt(path))

        def on_dialog_cancel():
            self.window.close_dialog()

        dlg = gui.FileDialog(gui.FileDialog.OPEN, "Select COLMAP images.txt", self.window.theme)
        dlg.add_filter(".txt", "COLMAP images.txt")
        dlg.set_path(self.output_dir)
        dlg.set_on_done(on_dialog_done)
        dlg.set_on_cancel(on_dialog_cancel)
        self.window.show_dialog(dlg)

    def _parse_images_txt(self, path):
        imported_annotations = {f: {} for f in self.image_files}
        imported_metadata = {f: None for f in self.image_files}
        local_max_point3d_id = 0
        feature_id_counter = 1

        try:
            with open(path, 'r') as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                i += 1
                if not line or line.startswith('#'):
                    continue

                parts = line.split()
                if len(parts) < 10:
                    continue

                image_name = parts[9]

                matched_name = None
                if image_name in self.image_files:
                    matched_name = image_name
                else:
                    base_name = os.path.basename(image_name)
                    if base_name in self.image_files:
                        matched_name = base_name

                if not matched_name:
                    continue

                metadata = {
                    'QW': parts[1], 'QX': parts[2], 'QY': parts[3], 'QZ': parts[4],
                    'TX': parts[5], 'TY': parts[6], 'TZ': parts[7],
                    'CAMERA_ID': parts[8],
                    'IMAGE_ID': parts[0]
                }
                imported_metadata[matched_name] = metadata

                if i < len(lines):
                    line = lines[i].strip()
                    i += 1
                    if line.startswith('#'):
                        continue

                    keypoint_data = line.split()

                    if len(keypoint_data) % 3 != 0:
                        continue

                    num_keypoints = len(keypoint_data) // 3

                    for j in range(num_keypoints):
                        try:
                            x = float(keypoint_data[j * 3])
                            y = float(keypoint_data[j * 3 + 1])
                            point3d_id = int(keypoint_data[j * 3 + 2])
                        except ValueError:
                            continue

                        imported_annotations[matched_name][feature_id_counter] = (
                            x, y, DEFAULT_DESCRIPTOR, DEFAULT_SCALE, DEFAULT_ANGLE, point3d_id
                        )

                        if point3d_id > 0:
                            local_max_point3d_id = max(local_max_point3d_id, point3d_id)

                        feature_id_counter += 1

        except Exception as e:
            print(f"Error parsing images.txt: {e}")
            return None, None, 0

        return imported_annotations, imported_metadata, local_max_point3d_id

    def _on_import_images_txt(self, path):
        annotations, metadata, max_3d_id = self._parse_images_txt(path)

        if annotations is None:
            self._show_message("Error", "Failed to parse images.txt file.")
            return

        self.annotations = annotations
        self.image_metadata = metadata
        self.max_point3d_id = max_3d_id

        all_feature_ids = [fid for annots in self.annotations.values() for fid in annots.keys()]
        if all_feature_ids:
            self.current_feature_id = max(all_feature_ids) + 1
        else:
            self.current_feature_id = 1

        self.app.post_to_main_thread(self.window, lambda: setattr(self.id_input, 'int_value', self.current_feature_id))
        self.app.post_to_main_thread(self.window, self._update_display_images)
        self.app.post_to_main_thread(self.window, lambda: self._show_message("Success",
                                                                            f"Imported images.txt.\nMax 3D ID found: {self.max_point3d_id}"))

    def _on_export_images_txt(self):
        print("正在导出修正后的 images.txt...")

        output_lines = []
        output_filepath = os.path.join(self.output_dir, "corrected_images.txt")

        all_names = sorted(self.image_files)

        exported_count = 0

        for idx, img_name in enumerate(all_names):
            metadata = self.image_metadata.get(img_name)
            annotations = self.annotations.get(img_name, {})

            if metadata is None:
                image_id = idx + 1
                qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
                tx, ty, tz = 0.0, 0.0, 0.0
                camera_id = 1
            else:
                image_id = metadata['IMAGE_ID']
                qw, qx, qy, qz = metadata['QW'], metadata['QX'], metadata['QY'], metadata['QZ']
                tx, ty, tz = metadata['TX'], metadata['TY'], metadata['TZ']
                camera_id = metadata['CAMERA_ID']

            line1 = f"{image_id} {qw} {qx} {qy} {qz} {tx} {ty} {tz} {camera_id} {img_name}\n"
            output_lines.append(line1)

            keypoint_str = []
            if annotations:
                sorted_annotations = sorted(annotations.items(), key=lambda item: item[0])
                for fid, data in sorted_annotations:
                    x, y, _, _, _, point3d_id = data
                    keypoint_str.append(f"{x:.6f} {y:.6f} {point3d_id}")

            line2 = " ".join(keypoint_str) + "\n"
            output_lines.append(line2)
            exported_count += 1

        try:
            with open(output_filepath, 'w') as f:
                f.write("# Corrected image list generated by ManualFeatureAnnotator\n")
                f.write("# Format: IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
                f.write("#         POINTS2D[] as (X, Y, POINT3D_ID)\n")
                f.write(f"# Number of images: {exported_count}, mean observations per image: N/A\n")
                f.writelines(output_lines)

            self.app.post_to_main_thread(self.window,
                                         lambda: self._show_message("Success",
                                                                    f"Exported {exported_count} images to {output_filepath}"))
        except Exception as e:
            self.app.post_to_main_thread(self.window,
                                         lambda: self._show_message("Error", f"Failed to save images.txt: {e}"))
