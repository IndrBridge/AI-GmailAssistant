const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

// Read manifest template
const manifestPath = path.join(__dirname, '..', 'extension', 'manifest.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

// Replace client ID
manifest.oauth2.client_id = process.env.GOOGLE_OAUTH_CLIENT_ID;

// Write updated manifest
fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
