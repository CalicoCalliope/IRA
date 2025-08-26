import express from "express";
import dotenv from "dotenv";
import pemRoutes from "./routes/pemRoutes";

dotenv.config();

const app = express();
app.use(express.json());

// Routes
app.use("/pems", pemRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[Coordinator Service] running on port ${PORT}`);
});