# CNN Model Setup Guide

## Warning: "CNN model module not available. Image-based detection disabled"

This warning appears when TensorFlow is not installed in your Python environment.

## Impact

- ✅ **Text-based disease detection still works** - You can still diagnose diseases by describing symptoms
- ❌ **Image-based disease detection is disabled** - You cannot upload images for automatic disease detection

## Solution Options

### Option 1: Install TensorFlow (Recommended if you want image detection)

Install TensorFlow and dependencies:

```bash
pip install tensorflow>=2.13.0
```

**Note:** TensorFlow can be large (~500MB-2GB) and may take time to install.

### Option 2: Use CPU-only TensorFlow (Lighter)

If you don't have a GPU, use the CPU-only version:

```bash
pip install tensorflow-cpu>=2.13.0
```

### Option 3: Ignore the Warning (Text-only mode)

If you only need text-based disease detection and don't need image uploads:
- The warning is harmless
- All other features (disease text diagnosis, price, buyer connect, schemes) work fine
- You can suppress the warning if desired

## Verify Installation

After installing TensorFlow, restart your backend and check:

```bash
python -c "from cnn_model import PlantDiseaseCNN; print('CNN model available!')"
```

You should see: `CNN model available!`

## Model File

The system expects `plantvillage_cnn_model.h5` to be in the project root directory. If the model file is missing, you'll see a different warning when trying to use image detection.

## Current Status

Based on your terminal output:
- ❌ TensorFlow not installed
- ✅ Model file exists (`plantvillage_cnn_model.h5`)
- ✅ Text-based disease detection: **Working**
- ❌ Image-based disease detection: **Disabled**

## Quick Fix

If you want to enable image detection:

```bash
pip install tensorflow>=2.13.0
```

Then restart your backend server.

