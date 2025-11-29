from .annotator import ManualFeatureAnnotator

def main():
    IMG_FOLDER = ""
    annotator = ManualFeatureAnnotator(IMG_FOLDER, output_dir="colmap_manual_output")
    annotator.run()

if __name__ == "__main__":
    main()
