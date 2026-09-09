// server.js
// ============================================================
// NJANGI TRACKER SERVER
// ============================================================
// This file is intentionally kept simple.
//
// Its main job is:
// 1. Start the web server.
// 2. Receive requests from the website.
// 3. Call the right helper function.
// 4. Send a response back.
//
// Database work is in database.js.
// Member work is in members.js.
// Contribution work is in contributions.js.
// Cycle work is in cycles.js.
// Loan work is in loans.js.
// Login helpers are in auth.js.
// ============================================================

const http = require("http");
const path = require("path");
const fs = require("fs");

const { loadDB, saveDB } = require("./database");
const members = require("./members");
const contributions = require("./contributions");
const cycles = require("./cycles");
const loans = require("./loans");
const auth = require("./auth");

const PORT = process.env.PORT || 3000;
const WEBSITE_FOLDER = path.join(__dirname, "..");

// -------------------------
// Small helper functions
// -------------------------

function sendJSON(response, statusCode, data) {
    response.writeHead(statusCode, {
        "Content-Type": "application/json"
    });

    response.end(JSON.stringify(data));
}

function readRequestBody(request) {
    return new Promise((resolve, reject) => {
        let body = "";

        request.on("data", chunk => {
            body += chunk;
        });

        request.on("end", () => {
            if (!body) {
                resolve({});
                return;
            }

            try {
                resolve(JSON.parse(body));
            } catch (error) {
                reject(error);
            }
        });
    });
}

function makeId(prefix) {
    return prefix + "_" + Date.now();
}

// -------------------------
// Create the server
// -------------------------

const server = http.createServer(async (request, response) => {

    // The URL tells us what the visitor wants.
    const url = new URL(request.url, `http://localhost:${PORT}`);

    // Load our database.
    const db = loadDB();

    // --------------------------------------------------------
    // 1. Health check
    // --------------------------------------------------------

    if (url.pathname === "/api/health") {
        sendJSON(response, 200, {
            ok: true,
            message: "Njangi Tracker server is working"
        });
        return;
    }

    // --------------------------------------------------------
    // 2. Public members
    // --------------------------------------------------------

    if (url.pathname === "/api/members/public" && request.method === "GET") {
        sendJSON(response, 200, members.getMembers(db));
        return;
    }

    // --------------------------------------------------------
    // 3. Get all members
    // --------------------------------------------------------

    if (url.pathname === "/api/members" && request.method === "GET") {
        sendJSON(response, 200, members.getMembers(db));
        return;
    }

    // --------------------------------------------------------
    // 4. Add a member
    // --------------------------------------------------------

    if (url.pathname === "/api/members" && request.method === "POST") {
        try {
            const body = await readRequestBody(request);

            const newMember = {
                id: makeId("member"),
                name: body.name,
                email: body.email || "",
                phone: body.phone || "",
                expected: Number(body.expected || 0),
                enrolled: true,
                rotationPosition: Number(body.rotationPosition || 0)
            };

            members.addMember(db, newMember);
            saveDB(db);

            sendJSON(response, 201, newMember);
        } catch (error) {
            sendJSON(response, 400, {
                error: "Could not add member"
            });
        }

        return;
    }

    // --------------------------------------------------------
    // 5. Edit a member
    // --------------------------------------------------------

    if (url.pathname.startsWith("/api/members/") &&
        request.method === "PUT") {

        const id = url.pathname.split("/")[3];

        try {
            const body = await readRequestBody(request);

            const updated = members.updateMember(db, id, body);

            if (!updated) {
                sendJSON(response, 404, {
                    error: "Member not found"
                });
                return;
            }

            saveDB(db);
            sendJSON(response, 200, updated);
        } catch (error) {
            sendJSON(response, 400, {
                error: "Could not update member"
            });
        }

        return;
    }

    // --------------------------------------------------------
    // 6. Delete a member
    // --------------------------------------------------------

    if (url.pathname.startsWith("/api/members/") &&
        request.method === "DELETE") {

        const id = url.pathname.split("/")[3];

        const deleted = members.deleteMember(db, id);

        if (!deleted) {
            sendJSON(response, 404, {
                error: "Member not found"
            });
            return;
        }

        saveDB(db);

        sendJSON(response, 200, {
            message: "Member deleted"
        });

        return;
    }

    // --------------------------------------------------------
    // 7. Contributions
    // --------------------------------------------------------

    if (url.pathname === "/api/contributions" &&
        request.method === "GET") {

        sendJSON(response, 200, contributions.getContributions(db));
        return;
    }

    if (url.pathname === "/api/contributions" &&
        request.method === "POST") {

        try {
            const body = await readRequestBody(request);

            const contribution = {
                id: makeId("contribution"),
                memberId: body.memberId,
                memberName: body.memberName || "",
                amount: Number(body.amount || 0),
                date: body.date || new Date().toISOString().slice(0, 10)
            };

            contributions.addContribution(db, contribution);
            saveDB(db);

            sendJSON(response, 201, contribution);
        } catch (error) {
            sendJSON(response, 400, {
                error: "Could not add contribution"
            });
        }

        return;
    }

    // --------------------------------------------------------
    // 8. Cycles
    // --------------------------------------------------------

    if (url.pathname === "/api/cycles" &&
        request.method === "GET") {

        sendJSON(response, 200, cycles.getCycles(db));
        return;
    }

    if (url.pathname === "/api/cycles" &&
        request.method === "POST") {

        try {
            const body = await readRequestBody(request);

            const cycle = {
                id: makeId("cycle"),
                number: Number(body.number || db.cycles.length + 1),
                target: Number(body.target || 0),
                startDate: body.startDate || "",
                endDate: body.endDate || "",
                recipientId: body.recipientId || "",
                status: "active"
            };

            cycles.addCycle(db, cycle);
            saveDB(db);

            sendJSON(response, 201, cycle);
        } catch (error) {
            sendJSON(response, 400, {
                error: "Could not add cycle"
            });
        }

        return;
    }

    if (url.pathname.startsWith("/api/cycles/") &&
        url.pathname.endsWith("/close") &&
        request.method === "POST") {

        const parts = url.pathname.split("/");
        const id = parts[3];

        const cycle = cycles.closeCycle(db, id);

        if (!cycle) {
            sendJSON(response, 404, {
                error: "Cycle not found"
            });
            return;
        }

        saveDB(db);
        sendJSON(response, 200, cycle);
        return;
    }

    // --------------------------------------------------------
    // 9. Loans
    // --------------------------------------------------------

    if (url.pathname === "/api/loans" &&
        request.method === "GET") {

        sendJSON(response, 200, loans.getLoans(db));
        return;
    }

    if (url.pathname === "/api/loans" &&
        request.method === "POST") {

        try {
            const body = await readRequestBody(request);

            const loan = {
                id: makeId("loan"),
                memberId: body.memberId || "",
                memberName: body.memberName || "",
                requestedAmount: Number(body.requestedAmount || 0),
                balance: Number(body.requestedAmount || 0),
                status: "pending",
                createdAt: new Date().toISOString()
            };

            loans.addLoan(db, loan);
            saveDB(db);

            sendJSON(response, 201, loan);
        } catch (error) {
            sendJSON(response, 400, {
                error: "Could not create loan request"
            });
        }

        return;
    }

    if (url.pathname.startsWith("/api/loans/") &&
        url.pathname.endsWith("/approve") &&
        request.method === "POST") {

        const id = url.pathname.split("/")[3];
        const loan = loans.approveLoan(db, id);

        if (!loan) {
            sendJSON(response, 404, {
                error: "Loan not found"
            });
            return;
        }

        saveDB(db);
        sendJSON(response, 200, loan);
        return;
    }

    if (url.pathname.startsWith("/api/loans/") &&
        url.pathname.endsWith("/reject") &&
        request.method === "POST") {

        const id = url.pathname.split("/")[3];
        const loan = loans.rejectLoan(db, id);

        if (!loan) {
            sendJSON(response, 404, {
                error: "Loan not found"
            });
            return;
        }

        saveDB(db);
        sendJSON(response, 200, loan);
        return;
    }

    // --------------------------------------------------------
    // 10. Serve the website
    // --------------------------------------------------------

    let filePath = url.pathname === "/"
        ? path.join(WEBSITE_FOLDER, "index.html")
        : path.join(WEBSITE_FOLDER, url.pathname);

    // Prevent paths from escaping the website folder.
    filePath = path.normalize(filePath);

    if (!filePath.startsWith(WEBSITE_FOLDER)) {
        sendJSON(response, 403, {
            error: "Not allowed"
        });
        return;
    }

    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {

        const extension = path.extname(filePath);

        const types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg"
        };

        const contentType = types[extension] || "text/plain";

        response.writeHead(200, {
            "Content-Type": contentType
        });

        response.end(fs.readFileSync(filePath));
        return;
    }

    // Nothing matched.
    sendJSON(response, 404, {
        error: "Page not found"
    });
});

// Start the server.
server.listen(PORT, () => {
    console.log("");
    console.log("Njangi Tracker is running!");
    console.log(`Open http://localhost:${PORT}`);
    console.log("");
});
