const express = require("express");
const router = express.Router();
const pool = require("../db");

// POST /api/calls
router.post("/", async (req, res) => {
  const data = req.body;

  const conn = await pool.getConnection();
  await conn.beginTransaction();

  try {
    // 1️⃣ Insert Caller
    const [callerResult] = await conn.query(
      `INSERT INTO Callers_Table 
        (Client_ID, Name, Caller_Email, Caller_Phone, Caller_Address)
       VALUES (?, ?, ?, ?, ?)`,
      [
        data.client.clientId,
        data.caller.name,
        data.caller.email,
        data.caller.phone,
        data.caller.address
      ]
    );

    const callerId = callerResult.insertId;

    // 2️⃣ Insert Call Details
    const [callResult] = await conn.query(
      `INSERT INTO Call_Detail_Table 
        (Caller_ID, Client_ID, From_Number, To_Number, Start_Time, End_Time, Duration)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        callerId,
        data.client.clientId,
        data.call.fromNumber,
        data.call.toNumber,
        data.call.startTime,
        data.call.endTime,
        data.call.duration
      ]
    );

    const callId = callResult.insertId;

    // 3️⃣ Insert Summary
    await conn.query(
      `INSERT INTO Summary_Table 
        (Call_ID, Service_Type, Issue_Description, Appointment_Date, Appointment_Time)
       VALUES (?, ?, ?, ?, ?)`,
      [
        callId,
        data.summary.serviceType,
        data.summary.issueDescription,
        data.summary.appointmentDate,
        data.summary.appointmentTime
      ]
    );

    await conn.commit();

    res.json({ success: true, callId });

  } catch (err) {
    console.error("❌ Insert Error:", err);
    await conn.rollback();
    res.status(500).json({ error: err.message });
  } finally {
    conn.release();
  }
});


module.exports = router;
