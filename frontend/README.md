# AgriMitra Frontend

A modern React frontend for the AgriMitra Agricultural Assistant system.

## Features

- 🎨 Beautiful, modern UI with gradient designs
- 🌾 Specialized display components for each agent type:
  - Disease Diagnosis with symptoms and treatments
  - Market Price with trends and recommendations
  - Buyer Connect with match scores and price suggestions
  - Government Schemes with eligibility and benefits
- 📱 Responsive design for mobile and desktop
- 📷 Image upload support for disease diagnosis
- 🔍 Real-time query processing
- 💡 Example queries for quick testing

## Installation

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Make sure the backend API is running:
```bash
# In the project root directory
uvicorn api:app --reload --port 8000
```

3. Start the React development server:
```bash
npm start
```

The app will open at `http://localhost:3000`

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── Header.js          # App header
│   │   ├── QueryInput.js      # Query input form
│   │   ├── ResponseDisplay.js # Main response container
│   │   └── agent-responses/
│   │       ├── DiseaseResponse.js
│   │       ├── PriceResponse.js
│   │       ├── BuyerConnectResponse.js
│   │       └── SchemeResponse.js
│   ├── App.js                 # Main app component
│   ├── App.css
│   ├── index.js
│   └── index.css
├── package.json
└── README.md
```

## Usage

1. Enter your query in the text area or click an example query
2. Optionally upload an image for disease diagnosis
3. Click "Ask AgriMitra" to process your query
4. View the structured response from the relevant agents

## Example Queries

- **Disease**: "My tomato leaves have yellow spots"
- **Price**: "What's the current price of rice?"
- **Buyer Connect**: "I want to sell my tomato crop"
- **Schemes**: "Show me agricultural schemes in Maharashtra"

## API Endpoints

The frontend communicates with the backend API:

- `POST /api/query` - Process text-only query
- `POST /api/query/upload` - Process query with image upload
- `GET /api/health` - Health check

## Customization

### Styling

All styles are in the respective CSS files:
- `App.css` - Main app styles
- Component-specific CSS files in each component directory

### Colors

The app uses a green color scheme:
- Primary: `#2d8659` (Green)
- Disease: `#e74c3c` (Red)
- Price: `#f39c12` (Orange)
- Buyer Connect: `#3498db` (Blue)
- Schemes: `#9b59b6` (Purple)

## Build for Production

```bash
npm run build
```

This creates an optimized production build in the `build` folder.

## Troubleshooting

1. **CORS Errors**: Make sure the backend API has CORS enabled for `http://localhost:3000`

2. **API Connection Failed**: 
   - Check if the backend is running on port 8000
   - Verify the proxy setting in `package.json`

3. **Module Not Found**: Run `npm install` to install dependencies

