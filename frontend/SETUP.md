# How to Run the AgriMitra Frontend

## Prerequisites

1. **Node.js and npm** installed on your system
   - Check if installed: `node --version` and `npm --version`
   - If not installed, download from: https://nodejs.org/

2. **Python backend** should be running (see step 2 below)

## Step-by-Step Instructions

### Step 1: Install Frontend Dependencies

Open a terminal in the `frontend` directory and run:

```bash
cd frontend
npm install
```

This will install all required React packages (react, react-dom, axios, etc.)

### Step 2: Start the Backend API

**In a separate terminal window**, navigate to the project root and start the FastAPI server:

```bash
# From project root directory
uvicorn api:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Important:** Keep this terminal window open while using the frontend.

### Step 3: Start the React Development Server

**In the frontend terminal**, run:

```bash
npm start
```

The React app will automatically open in your browser at `http://localhost:3000`

If it doesn't open automatically, manually navigate to: `http://localhost:3000`

## Quick Start (All Commands)

```bash
# Terminal 1 - Start Backend
cd D:\Agrimitra-copy
uvicorn api:app --reload --port 8000

# Terminal 2 - Start Frontend
cd D:\Agrimitra-copy\frontend
npm install  # First time only
npm start
```

## Troubleshooting

### Issue: "npm: command not found"
**Solution:** Install Node.js from https://nodejs.org/

### Issue: "Cannot find module" errors
**Solution:** Run `npm install` again in the frontend directory

### Issue: "CORS error" or "Network error" when submitting queries
**Solutions:**
- Make sure the backend is running on port 8000
- Check that `api.py` is in the project root
- Verify CORS settings in `api.py` allow `http://localhost:3000`

### Issue: "Module not found: Can't resolve 'axios'"
**Solution:** Run `npm install axios` in the frontend directory

### Issue: Backend not responding
**Solution:**
- Check if backend is running: `curl http://localhost:8000/api/health`
- Verify all Python dependencies are installed: `pip install -r requirements.txt`
- Check for errors in the backend terminal

### Issue: Port 3000 already in use
**Solution:** React will ask if you want to use a different port. Press 'Y' to confirm, or:
- Kill the process using port 3000
- Or change the port in `package.json` scripts: `"start": "PORT=3001 react-scripts start"`

## Testing the Frontend

Once both servers are running:

1. Open `http://localhost:3000` in your browser
2. Try the example queries by clicking the chips, or type your own query
3. Click "Ask AgriMitra" to process your query
4. View the structured response from the relevant agents

## Production Build (Optional)

To create an optimized production build:

```bash
cd frontend
npm run build
```

This creates a `build` folder with optimized static files that can be served by any web server.

