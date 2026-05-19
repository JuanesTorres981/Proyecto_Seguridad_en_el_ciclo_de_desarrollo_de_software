import { useState } from "react";

function App() {
  const [amount, setAmount] = useState("");
  const [country, setCountry] = useState("");
  const [userId, setUserId] = useState("");
  const [frequency, setFrequency] = useState("");
  const [hour, setHour] = useState("");
  const [result, setResult] = useState(null);

  const analyzeTransaction = async () => {
    const response = await fetch(
      "/api/transactions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          amount: Number(amount),
          location: country,
          user_id: userId,
          frequency: Number(frequency),
          hour: Number(hour),
          is_new_account: false
}),
        }),
      }
    );

    const data = await response.json();

    setResult(data);
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h2 style={styles.title}>
          Bubbles tu detectora de Fraude 🫧
        </h2>

        <p style={styles.subtitle}>
          Analiza transacciones sospechosas en tiempo real
        </p>

        <input
          type="number"
          placeholder="Monto de la transacción"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          style={styles.input}
        />

        <input
          type="text"
          placeholder="País"
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          style={styles.input}
        />
        <input
          type="text"
          placeholder="User ID"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          style={styles.input}
        />

        <input
          type="number"
          placeholder="Frecuencia"
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
          style={styles.input}
        />

        <input
          type="number"
          placeholder="Hora"
          value={hour}
          onChange={(e) => setHour(e.target.value)}
          style={styles.input}
        />
        <button
          onClick={analyzeTransaction}
          style={styles.button}
        >
          Analizar Transacción
        </button>

        {result && (
          <div style={styles.resultBox}>
            <h2>Resultado</h2>

            <pre style={styles.pre}>
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  page: {
    backgroundColor: "#4B92DB",
    minHeight: "100vh",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontFamily: "Arial",
    padding: "20px",
  },

  card: {
    backgroundColor: "#0087BD",
    padding: "40px",
    borderRadius: "20px",
    width: "400px",
    boxShadow: "0 0 30px rgba(0,0,0,0.3)",
  },

  title: {
    color: "white",
    marginBottom: "10px",
  },

  subtitle: {
    color: "#94a3b8",
    marginBottom: "30px",
  },

  input: {
    width: "100%",
    padding: "12px",
    marginBottom: "15px",
    borderRadius: "10px",
    border: "none",
    backgroundColor: "#334155",
    color: "white",
    fontSize: "16px",
  },

  button: {
    width: "100%",
    padding: "14px",
    borderRadius: "10px",
    border: "none",
    backgroundColor: "#2563eb",
    color: "white",
    fontSize: "16px",
    cursor: "pointer",
  },

  resultBox: {
    marginTop: "25px",
    backgroundColor: "#0f172a",
    padding: "20px",
    borderRadius: "10px",
    color: "white",
  },

  pre: {
    whiteSpace: "pre-wrap",
  },
};

export default App;