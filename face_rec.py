import face_recognition
import openpyxl
import os
import cv2
import shutil

# --- Configuration ---
# You would need to create a directory with subdirectories for each person's reference image
# and a file known_faces.xlsx that maps names to images.
# For example:
# known_faces_images/
# ├── john_doe.jpg
# └── jane_smith.jpg

# The excel sheet should have two columns: 'Name' and 'Image Path'
# Name         | Image Path
# ------------|--------------------------
# John Doe    | known_faces_images/john_doe.jpg
# Jane Smith  | known_faces_images/jane_smith.jpg

EXCEL_FILE = "known_faces.xlsx"
SORTED_FILES_DIR = "sorted_files"
UNKNOWN_FACES_DIR = os.path.join(SORTED_FILES_DIR, "unidentified")
TEMP_UPLOAD_DIR = "temp_uploads"

# --- Main Logic ---

def load_known_faces():
    """
    Loads known face encodings and names from an Excel sheet.
    
    Returns:
        A tuple of two lists: known_face_encodings and known_face_names.
    """
    known_face_encodings = []
    known_face_names = []

    try:
        workbook = openpyxl.load_workbook(EXCEL_FILE)
        sheet = workbook.active
        print(f"Loading known faces from '{EXCEL_FILE}'...")

        for row in sheet.iter_rows(min_row=2, values_only=True):
            name, image_path = row
            if name and image_path:
                try:
                    # Load the image and get the face encoding
                    image = face_recognition.load_image_file(image_path)
                    face_encoding = face_recognition.face_encodings(image)[0]
                    known_face_encodings.append(face_encoding)
                    known_face_names.append(name)
                    print(f"Loaded face for: {name}")
                except IndexError:
                    print(f"Warning: No face found in image for {name} at {image_path}")
                except FileNotFoundError:
                    print(f"Error: Image file not found at {image_path} for {name}")

    except FileNotFoundError:
        print(f"Error: The Excel file '{EXCEL_FILE}' was not found.")
    
    return known_face_encodings, known_face_names

def process_image(image_path, known_encodings, known_names):
    """
    Processes an image file to find and identify faces.
    
    Returns:
        The name of the identified person, or None if no match is found.
    """
    print(f"Processing image: {image_path}")
    try:
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            name = "Unknown"

            if True in matches:
                first_match_index = matches.index(True)
                name = known_names[first_match_index]
                return name
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
    
    return None

def process_video(video_path, known_encodings, known_names):
    """
    Processes a video file to find and identify faces in frames.
    
    Returns:
        The name of the identified person, or None if no match is found.
    """
    print(f"Processing video: {video_path}")
    video_capture = cv2.VideoCapture(video_path)
    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)
    frame_interval = int(frame_rate * 5) # Check every 5 seconds

    frame_count = 0
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            # Process frame if it's at the desired interval
            rgb_frame = frame[:, :, ::-1] # Convert BGR to RGB
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_encodings, face_encoding)
                if True in matches:
                    first_match_index = matches.index(True)
                    name = known_names[first_match_index]
                    print(f"Face recognized in video frame: {name}")
                    video_capture.release()
                    return name
        
        frame_count += 1

    video_capture.release()
    return None

def sort_file(file_path, person_name):
    """
    Moves a file to the appropriate person's folder.
    """
    target_dir = os.path.join(SORTED_FILES_DIR, person_name)
    os.makedirs(target_dir, exist_ok=True)
    
    shutil.move(file_path, target_dir)
    print(f"File '{os.path.basename(file_path)}' sorted to '{target_dir}'")

def main():
    """
    Main function to run the file processing and sorting logic.
    
    Note: This is a conceptual script. In a real application, a web server
    (like Flask) would handle file uploads and pass the file paths to this
    logic. The 'temp_uploads' directory here simulates that process.
    """
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    os.makedirs(UNKNOWN_FACES_DIR, exist_ok=True)

    # Simulate some files being uploaded
    # You would replace this with actual logic to handle files uploaded by users.
    print(f"Simulating file uploads to '{TEMP_UPLOAD_DIR}'...")
    # Example: Create dummy files for demonstration
    with open(os.path.join(TEMP_UPLOAD_DIR, "test_image.jpg"), "w") as f:
        f.write("dummy content")
    with open(os.path.join(TEMP_UPLOAD_DIR, "test_video.mp4"), "w") as f:
        f.write("dummy content")
    
    # 1. Load the known faces
    known_face_encodings, known_face_names = load_known_faces()
    if not known_face_encodings:
        print("No known faces loaded. Exiting.")
        return

    # 2. Process the uploaded files
    for filename in os.listdir(TEMP_UPLOAD_DIR):
        file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        person_name = None
        if file_ext in ['.jpg', '.jpeg', '.png']:
            person_name = process_image(file_path, known_face_encodings, known_face_names)
        elif file_ext in ['.mp4', '.webm']:
            person_name = process_video(file_path, known_face_encodings, known_face_names)
        else:
            print(f"Skipping unsupported file type: {filename}")
            person_name = "unidentified"

        # 3. Sort the file
        if person_name:
            sort_file(file_path, person_name)
        else:
            sort_file(file_path, "unidentified")

if name == "main":
    main()