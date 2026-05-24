import os
import shutil
import tempfile
import random
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, WeightedRandomSampler, Dataset
from torchvision import datasets, transforms, models
from PIL import Image

# =========================
# SOPORTE HEIC
# =========================

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    print("HEIC habilitado.")
except ImportError:
    print("pillow_heif no instalado — archivos HEIC serán ignorados.")

# =========================
# CONFIG
# =========================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {DEVICE}")

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "Lab_aforo")
MODEL_DIR   = os.path.join(BASE_DIR, "models")
MODEL_PATH  = os.path.join(MODEL_DIR, "cnn_hibrida.pth")

os.makedirs(MODEL_DIR, exist_ok=True)

TEMP_DATASET = tempfile.mkdtemp()
print(f"Dataset temporal: {TEMP_DATASET}")

# =========================
# EXTENSIONES VALIDAS
# =========================

VALID_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".tiff", ".tif"}

# =========================
# DIAGNOSTICO DE DATASET_DIR
# =========================

print(f"\n{'='*60}")
print(f"DIAGNOSTICO: {DATASET_DIR}")
print(f"{'='*60}")

if not os.path.exists(DATASET_DIR):
    raise FileNotFoundError(f"No se encontro la carpeta: {DATASET_DIR}")

all_entries = os.listdir(DATASET_DIR)
print(f"Carpetas encontradas ({len(all_entries)}):")
for e in all_entries:
    full_path = os.path.join(DATASET_DIR, e)
    if os.path.isdir(full_path):
        # Contar archivos totales incluyendo subcarpetas
        total_files = sum(len(files) for _, _, files in os.walk(full_path))
        print(f"  [DIR] '{e}'  — {total_files} archivos (incluyendo subcarpetas)")
    else:
        print(f"  [FILE] '{e}'")

print(f"{'='*60}\n")

# =========================
# MAPEAR CARPETAS A CLASES
# =========================

keyword_to_class = {
    "disponible": "Disponible",
    "lleno":      "Lleno",
    "vac":        "Vacio",
}

classes = {}
for folder in all_entries:
    if not os.path.isdir(os.path.join(DATASET_DIR, folder)):
        continue
    folder_lower = folder.lower()
    for keyword, label in keyword_to_class.items():
        if keyword in folder_lower:
            classes[folder] = label
            print(f"Mapeado: '{folder}' -> '{label}'")
            break

if len(classes) < 3:
    raise RuntimeError(
        f"Solo se detectaron {len(classes)} clases: {list(classes.values())}.\n"
        "Se necesitan 3 carpetas (Disponible, Lleno, Vacio)."
    )

# =========================
# CONVERTIR IMAGENES A JPG
# Recorre subcarpetas recursivamente con os.walk
# =========================

total_images = 0

for original_folder, new_folder in classes.items():

    src_folder = os.path.join(DATASET_DIR, original_folder)
    dst_folder = os.path.join(TEMP_DATASET, new_folder)
    os.makedirs(dst_folder, exist_ok=True)

    print(f"\n[{new_folder}] Escaneando: {src_folder}")

    count        = 0
    skipped      = 0
    onedrive_err = 0
    img_counter  = 0

    # os.walk entra en fisica/, grafica/, informatica/, etc.
    for root, dirs, files in os.walk(src_folder):
        subfolder_rel = os.path.relpath(root, src_folder)

        for file in files:
            ext = os.path.splitext(file)[1].lower()

            if ext not in VALID_EXT:
                skipped += 1
                continue

            src_path  = os.path.join(root, file)
            file_size = os.path.getsize(src_path)

            # OneDrive placeholder: 0 bytes
            if file_size == 0:
                onedrive_err += 1
                continue

            try:
                img = Image.open(src_path).convert("RGB")

                # Nombre unico: evita colisiones entre subcarpetas
                safe_sub  = subfolder_rel.replace(os.sep, "_").replace(".", "")
                base_name = os.path.splitext(file)[0]
                new_name  = f"{safe_sub}_{base_name}_{img_counter}.jpg"
                img_counter += 1

                dst_path = os.path.join(dst_folder, new_name)
                img.save(dst_path, "JPEG", quality=95)
                count        += 1
                total_images += 1

            except Exception as e:
                print(f"  Error en '{file}': {e}")

    print(f"  Convertidas : {count}")
    print(f"  Ext invalida: {skipped}")
    if onedrive_err > 0:
        print(f"  OneDrive (0 bytes): {onedrive_err} archivos no descargados")
        print(f"  -> Clic derecho en Lab_aforo -> 'Mantener siempre en este dispositivo'")

print(f"\nTotal imagenes listas: {total_images}")

if total_images == 0:
    shutil.rmtree(TEMP_DATASET)
    raise RuntimeError(
        "No se convirtio ninguna imagen.\n"
        "Verifica que las imagenes esten dentro de las subcarpetas\n"
        "(fisica, grafica, informatica, ingenieros, zonaestudio)\n"
        "y que no sean placeholders de OneDrive (0 bytes)."
    )

# =========================
# TRANSFORMACIONES
# =========================

train_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(p=0.1),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.1),
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# =========================
# DATASET BASE (sin transform para poder hacer split)
# =========================

full_dataset = datasets.ImageFolder(TEMP_DATASET, transform=None)

print(f"\nClases detectadas: {full_dataset.classes}")
print(f"Total imagenes   : {len(full_dataset)}")

class_counts = Counter(label for _, label in full_dataset.samples)
print("\nDistribucion por clase:")
for idx, name in enumerate(full_dataset.classes):
    print(f"  {name}: {class_counts[idx]} imagenes")

# =========================
# SPLIT ESTRATIFICADO 80/20
# =========================

random.seed(42)
torch.manual_seed(42)

indices_by_class = {i: [] for i in range(len(full_dataset.classes))}
for idx, (_, label) in enumerate(full_dataset.samples):
    indices_by_class[label].append(idx)

train_indices, val_indices = [], []

for label, idxs in indices_by_class.items():
    random.shuffle(idxs)
    split = int(0.8 * len(idxs))
    train_indices.extend(idxs[:split])
    val_indices.extend(idxs[split:])

print(f"\nTrain: {len(train_indices)} | Val: {len(val_indices)}")

# =========================
# DATASET CON TRANSFORM POR SEPARADO
# Lee PIL directo desde disco — no pasa por ImageFolder.__getitem__
# =========================

class TransformSubset(Dataset):
    def __init__(self, base_dataset, indices, transform):
        self.base      = base_dataset
        self.indices   = indices
        self.transform = transform

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        path, label = self.base.samples[self.indices[i]]
        img = Image.open(path).convert("RGB")
        return self.transform(img), label

train_dataset = TransformSubset(full_dataset, train_indices, train_transform)
val_dataset   = TransformSubset(full_dataset, val_indices,   val_transform)

# =========================
# WEIGHTED SAMPLER
# =========================

train_labels       = [full_dataset.samples[i][1] for i in train_indices]
class_counts_train = Counter(train_labels)
class_weights      = {c: 1.0 / n for c, n in class_counts_train.items()}
sample_weights     = [class_weights[lbl] for lbl in train_labels]

sampler = WeightedRandomSampler(
    weights=sample_weights,
    num_samples=len(train_indices),
    replacement=True,
)

# =========================
# DATALOADERS
# =========================

train_loader = DataLoader(train_dataset, batch_size=32,
                          sampler=sampler, num_workers=0)
val_loader   = DataLoader(val_dataset,   batch_size=32,
                          shuffle=False,  num_workers=0)

# =========================
# MODELO: EfficientNet-B0
# =========================

model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)

for param in model.parameters():
    param.requires_grad = True

in_features      = model.classifier[1].in_features
model.classifier = nn.Sequential(
    nn.Dropout(p=0.4),
    nn.Linear(in_features, 3),
)

model = model.to(DEVICE)
print(f"\nParametros entrenables: "
      f"{sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

# =========================
# LOSS / OPTIMIZER / SCHEDULER
# =========================

criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

optimizer = optim.AdamW([
    {"params": model.features.parameters(),   "lr": 1e-4},
    {"params": model.classifier.parameters(), "lr": 5e-4},
], weight_decay=1e-4)

scheduler = optim.lr_scheduler.CosineAnnealingLR(
    optimizer, T_max=40, eta_min=1e-6
)

# =========================
# ENTRENAMIENTO
# =========================

EPOCHS   = 40
PATIENCE = 10

print("\nIniciando entrenamiento...\n")
print(f"{'Epoch':>6} | {'Loss':>8} | {'Train':>7} | {'Val':>7} | Estado")
print("-" * 52)

best_val_acc     = 0.0
patience_counter = 0

for epoch in range(1, EPOCHS + 1):

    # TRAIN
    model.train()
    running_loss, correct, total = 0.0, 0, 0

    for imgs, lbls in train_loader:
        imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
        optimizer.zero_grad()
        out  = model(imgs)
        loss = criterion(out, lbls)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        running_loss += loss.item()
        _, pred = torch.max(out, 1)
        total   += lbls.size(0)
        correct += (pred == lbls).sum().item()

    train_acc = 100 * correct / total
    avg_loss  = running_loss / len(train_loader)

    # VALIDATION
    model.eval()
    val_correct, val_total = 0, 0
    confusion = torch.zeros(3, 3, dtype=torch.int)

    with torch.no_grad():
        for imgs, lbls in val_loader:
            imgs, lbls = imgs.to(DEVICE), lbls.to(DEVICE)
            out = model(imgs)
            _, pred = torch.max(out, 1)
            val_total   += lbls.size(0)
            val_correct += (pred == lbls).sum().item()
            for t, p in zip(lbls.cpu(), pred.cpu()):
                confusion[t][p] += 1

    val_acc = 100 * val_correct / val_total
    scheduler.step()

    saved  = val_acc > best_val_acc
    estado = "✓ guardado" if saved else ""
    print(f"{epoch:>6} | {avg_loss:>8.4f} | {train_acc:>6.2f}% | {val_acc:>6.2f}% | {estado}")

    if saved:
        best_val_acc     = val_acc
        patience_counter = 0
        torch.save({
            "epoch":                epoch,
            "model_state_dict":     model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "val_acc":              val_acc,
            "classes":              full_dataset.classes,
        }, MODEL_PATH)
    else:
        patience_counter += 1

    if patience_counter >= PATIENCE:
        print(f"\nEarly stopping en epoch {epoch}.")
        break

    if epoch % 5 == 0:
        print(f"\n  Confusion val — epoch {epoch}:")
        header = "".join(f"  {c[:8]:>9}" for c in full_dataset.classes)
        print(f"  {'':12}{header}")
        for i, c in enumerate(full_dataset.classes):
            row = "".join(f"  {confusion[i][j]:>9}" for j in range(3))
            print(f"  {c[:12]:12}{row}")
        print()

# =========================
# RESULTADO FINAL
# =========================

print("\n" + "=" * 52)
print(f"  Entrenamiento finalizado")
print(f"  Mejor Val Accuracy : {best_val_acc:.2f}%")
print(f"  Modelo guardado en : {MODEL_PATH}")
print("=" * 52)

if best_val_acc >= 80:
    print("\n  Objetivo >=80% alcanzado!")
else:
    diff = 80 - best_val_acc
    print(f"\n  Faltaron {diff:.1f}pp para el 80%.")
    print("  Opciones:")
    print("  -> Mas imagenes por clase (>=200 recomendado)")
    print("  -> Cambiar efficientnet_b0 por efficientnet_b2")
    print("  -> Aumentar EPOCHS a 60 y PATIENCE a 15")

# =========================
# LIMPIAR TEMP
# =========================

shutil.rmtree(TEMP_DATASET)
print("\nDataset temporal eliminado.")