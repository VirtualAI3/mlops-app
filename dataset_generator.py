import os
import shutil
import random
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

# Configuración
raw_images_dir = 'raw_dataset/images/'
raw_labels_dir = 'raw_dataset/labels/'
dataset_dir = 'dataset'

train_ratio = 0.70
val_ratio = 0.20
test_ratio = 0.10

splits = ['train', 'val', 'test']

# Crear directorios
def create_dirs(base_dir, splits):
    for split in splits:
        os.makedirs(os.path.join(base_dir, split, 'images'), exist_ok=True)
        os.makedirs(os.path.join(base_dir, split, 'labels'), exist_ok=True)

# Limpiar contenido anterior
def clear_dirs(base_dir, splits):
    for split in splits:
        for sub in ['images', 'labels']:
            path = os.path.join(base_dir, split, sub)
            if os.path.exists(path):
                for f in os.listdir(path):
                    os.remove(os.path.join(path, f))

# Leer clases de un archivo label
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

def copy_file(src_dst):
    src, dst = src_dst
    shutil.copy(src, dst)

def run_dataset_generator():
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
        # Ajustar para que no haya pérdidas por redondeo
        n_test = total - n_train - n_val

        split_files['train'].update(available_imgs[:n_train])
        split_files['val'].update(available_imgs[n_train:n_train + n_val])
        split_files['test'].update(available_imgs[n_train + n_val:n_train + n_val + n_test])

        used_images.update(available_imgs)

    # Copiar archivos con paralelismo
    print("Copiando archivos a sus splits...")
    copy_tasks = []
    for split in splits:
        for img_file in split_files[split]:
            label_file = os.path.splitext(img_file)[0] + '.txt'
            src_img = os.path.join(raw_images_dir, img_file)
            src_lbl = os.path.join(raw_labels_dir, label_file)

            dst_img = os.path.join(dataset_dir, split, 'images', img_file)
            dst_lbl = os.path.join(dataset_dir, split, 'labels', label_file)

            copy_tasks.append((src_img, dst_img))
            copy_tasks.append((src_lbl, dst_lbl))

    with ThreadPoolExecutor(max_workers=8) as executor:
        executor.map(copy_file, copy_tasks)

    print(f'Datos divididos:')
    for split in splits:
        print(f'  {split}: {len(split_files[split])} imágenes')
