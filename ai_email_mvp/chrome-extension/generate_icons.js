const fs = require('fs');
const { createCanvas } = require('canvas');

// Function to create an icon
function createIcon(size) {
    const canvas = createCanvas(size, size);
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = '#1a73e8';
    ctx.fillRect(0, 0, size, size);

    // Simple "G" letter
    ctx.fillStyle = 'white';
    ctx.font = `bold ${size * 0.6}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('G', size/2, size/2);

    // Save the icon
    const buffer = canvas.toBuffer('image/png');
    fs.writeFileSync(`public/icon${size}.png`, buffer);
}

// Create icons of different sizes
[16, 48, 128].forEach(size => {
    createIcon(size);
});

console.log('Icons generated successfully!');
