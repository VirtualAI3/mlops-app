import os
import shutil
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2
import albumentations as A

# Configuración
raw_images_dir = 'raw_dataset/images/'
raw_labels_dir = 'raw_dataset/labels/'
dataset_dir = 'dataset'

train_ratio = 0.70
val_ratio = 0.20
test_ratio = 0.10

splits = ['train', 'val', 'test']

def create_dirs(base_dir, splits):
    for split in splits:
        os.makedirs(os.path.join(base_dir, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(base_dir, split, 'labels'), exist_ok=True)

def clear_dirs(base_dir, splits):
    for split in splits:
        for sub in ['images', 'labels']:
            path = os.path.join(base_dir, split, sub)
            if os.path.exists(path):
                for f in os.listdir(path):
                    os.remove(os.path.join(path, f))

def get_image_classes(label_path):
    classes = set()
    try:
        with open(label_path, 'r') as f:
            for line in f:
                if line.strip():
                    class_id = int(line.strip().split()[0])
                    classes.add(class_id)
    except Exception as e:
        print(f"Error leyendo {label_path}: {e}")
    return classes

def read_yolo_labels(label_path):
    boxes = []
    with open(label_path, 'r') as f:
        for line in f.readlines():
            cls, x_c, y_c, w, h = line.strip().split()
            boxes.append([int(cls), float(x_c), float(y_c), float(w), float(h)])
    return np.array(boxes)

def save_yolo_labels(label_path, boxes):
    with open(label_path, 'w') as f:
        for box in boxes:
            cls, x_c, y_c, w, h = box
            f.write(f"{int(cls)} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}\n")

def zoom_out(image, boxes, scale=0.7, color=(114,114,114)):
    h, w = image.shape[:2]
    new_h, new_w = int(h*scale), int(w*scale)
    small_img = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    canvas = np.full_like(image, color)
    top = (h - new_h) // 2
    left = (w - new_w) // 2
    canvas[top:top+new_h, left:left+new_w] = small_img

    offset_x = left / w
    offset_y = top / h
    boxes[:, 1] = boxes[:, 1] * scale + offset_x
    boxes[:, 2] = boxes[:, 2] * scale + offset_y
    boxes[:, 3] = boxes[:, 3] * scale
    boxes[:, 4] = boxes[:, 4] * scale

    return canvas, boxes

def apply_blur(image, blur_prob=0.5):
    transform = A.OneOf([
        A.GaussianBlur(blur_limit=(3,7), p=1),
        A.MedianBlur(blur_limit=7, p=1),
        A.MotionBlur(blur_limit=7, p=1),
    ], p=blur_prob)
    augmented = transform(image=image)
    return augmented['image']

def copy_file(src_dst):
    src, dst = src_dst
    shutil.copy(src, dst)

def process_and_copy_image(img_file, split, blur_prob=0.5, zoom_scale=0.7, augmentation_prob=0.5):
    """
    Procesa la imagen y label, aplicando aumento con cierta probabilidad,
    luego guarda en la carpeta destino.
    """
    label_file = os.path.splitext(img_file)[0] + '.txt'
    src_img_path = os.path.join(raw_images_dir, img_file)
    src_lbl_path = os.path.join(raw_labels_dir, label_file)

    dst_img_path = os.path.join(dataset_dir, split, 'images', img_file)
    dst_lbl_path = os.path.join(dataset_dir, split, 'labels', label_file)

    image = cv2.imread(src_img_path)
    if image is None:
        print(f"No se pudo leer imagen {src_img_path}")
        return

    if os.path.exists(src_lbl_path):
        boxes = read_yolo_labels(src_lbl_path)
    else:
        boxes = np.zeros((0,5))

    # Decidir si se aplica aumento (zoom + blur)
    if random.random() < augmentation_prob:
        image_zoom, boxes_zoom = zoom_out(image, boxes.copy(), scale=zoom_scale)
        image_aug = apply_blur(image_zoom, blur_prob=blur_prob)
        boxes_aug = boxes_zoom
    else:
        image_aug = image
        boxes_aug = boxes

    cv2.imwrite(dst_img_path, image_aug)
    save_yolo_labels(dst_lbl_path, boxes_aug)

def run_dataset_generator(augmentation_prob=0.5, blur_prob=0.5, zoom_scale=0.7):
    print("Creando y limpiando directorios...")
    create_dirs(dataset_dir, splits)
    clear_dirs(dataset_dir, splits)

    print("Listando imágenes y labels...")
    all_images = [f for f in os.listdir(raw_images_dir) if f.endswith(('.jpg', '.png'))]
    all_images = [f for f in all_images if os.path.exists(os.path.join(raw_labels_dir, os.path.splitext(f)[0] + '.txt'))]
    print(f"Total imágenes con label: {len(all_images)}")

    # Leer clases con paralelismo
    image_classes = dict()
    def process_image(img):
        label_path = os.path.join(raw_labels_dir, os.path.splitext(img)[0] + '.txt')
        return img, get_image_classes(label_path)

    with ThreadPoolExecutor() as executor:
        results = executor.map(process_image, all_images)
        for img, classes in results:
            image_classes[img] = classes

    # Mapear clases a imágenes
    class_to_images = defaultdict(set)
    for img, classes in image_classes.items():
        for c in classes:
            class_to_images[c].add(img)
    print(f"Total clases encontradas: {len(class_to_images)}")

    # Distribuir imágenes evitando duplicados
    used_images = set()
    split_files = {'train': set(), 'val': set(), 'test': set()}

    for cls, imgs in class_to_images.items():
        available_imgs = list(imgs - used_images)
        random.shuffle(available_imgs)
        total = len(available_imgs)
        if total == 0:
            continue

        n_train = int(total * train_ratio)
        n_val = int(total * val_ratio)
        n_test = total - n_train - n_val

        split_files['train'].update(available_imgs[:n_train])
        split_files['val'].update(available_imgs[n_train:n_train + n_val])
        split_files['test'].update(available_imgs[n_train + n_val:n_train + n_val + n_test])

        used_images.update(available_imgs)

    print("Procesando y copiando imágenes con aumentos...")
    tasks = []
    for split in splits:
        for img_file in split_files[split]:
            tasks.append((img_file, split, blur_prob, zoom_scale, augmentation_prob))

    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(lambda args: process_and_copy_image(*args), tasks)

    print(f'Datos divididos:')
    for split in splits:
        print(f'  {split}: {len(split_files[split])} imágenes')
