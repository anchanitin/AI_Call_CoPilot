const express = require("express");
const cors = require("cors");
require("dotenv").config();

const app = express();

app.use(cors());
app.use(express.json());

app.use("/api/calls", require("./routes/calls"));

app.listen(process.env.PORT, () => {
  console.log(`🚀 Backend API running on port ${process.env.PORT}`);
});
