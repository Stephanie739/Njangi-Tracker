// database.js
// This file has one main job:
// read information from db.json and save information to db.json.

const fs = require("fs");
const path = require("path");

// Find the database file.
const DB_FILE = path.join(__dirname, "data", "db.json");

// Read the database.
function loadDB() {
    const text = fs.readFileSync(DB_FILE, "utf8");
    return JSON.parse(text);
}

// Save the database.
function saveDB(db) {
    const text = JSON.stringify(db, null, 2);
    fs.writeFileSync(DB_FILE, text);
}

module.exports = {
    loadDB,
    saveDB
};
