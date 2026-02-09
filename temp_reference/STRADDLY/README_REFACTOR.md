# Straddly Project Refactor

This project has been converted from a flat structure of saved HTML pages into a modern, structured web project.

## New Structure

- `src/`: Source code directory.
  - `pages/`: Contains the cleaned-up HTML pages.
  - `assets/`: Shared resources.
    - `css/`: Common stylesheets (extracted from redundant files).
    - `js/`: Common JavaScript bundles (runtime, polyfills, etc.).
    - `img/`: Project images and logos.
- `public/`: Static assets that should be served as-is.
- `tools/`: Utility scripts for migration and maintenance.
- `package.json`: Project configuration and scripts.

## Benefits of the New Format

1.  **Reduced Redundancy**: Shared CSS and JS are now stored once in `assets/` instead of being duplicated in every `_files` folder.
2.  **Cleaner Organization**: Source files are separated from build artifacts and static assets.
3.  **Modern Build System**: Ready for integration with tools like Vite, Webpack, or Tailwind CSS.
4.  **Easier Maintenance**: Hashed file names have been simplified, and paths are now relative to the project root.

## How to use

1.  Install dependencies: `npm install`
2.  Start development server: `npm start`
3.  Build for production: `npm run build`

## Migration Tool

If you add new saved pages to the root, you can run `npm run migrate` to automatically clean them and move them to `src/pages`.
