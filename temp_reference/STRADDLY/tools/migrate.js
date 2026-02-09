const fs = require('fs');
const path = require('path');

const srcDir = './';
const destDir = './src/pages';

if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
}

const files = fs.readdirSync(srcDir);

files.forEach(file => {
    if (file.endsWith('.html') && file !== 'index.html' && !file.includes('src')) {
        console.log(`Processing ${file}...`);
        let content = fs.readFileSync(path.join(srcDir, file), 'utf8');
        
        // Extract the app-root content if possible, or just clean the HTML
        // Since these are saved pages, they have a lot of junk.
        // For a true migration, we'd want to extract the Angular state/components,
        // but for a "better format code" request, we'll focus on structure first.
        
        // Minimal cleaning: fix asset paths
        content = content.replace(/\.\/.*?_files\//g, '/assets/');
        content = content.replace(/styles\.[a-z0-9]+\.css/g, 'main.css');
        
        fs.writeFileSync(path.join(destDir, file), content);
    }
});

console.log('Migration complete.');
