from .annotator import ManualFeatureAnnotator

def main():
    IMG_FOLDER = "/home/sunboyi/BAAI/data/dreame-pose-refine/dreame-2f8403-20250421164957/images"
    annotator = ManualFeatureAnnotator(IMG_FOLDER, output_dir="colmap_manual_output")
    annotator.run()

if __name__ == "__main__":
    main()
