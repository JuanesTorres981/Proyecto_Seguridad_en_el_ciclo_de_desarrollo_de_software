import { useState } from "react";

function App() {
  const [amount, setAmount] = useState("");
  const [country, setCountry] = useState("");
  const [result, setResult] = useState(null);

  const analyzeTransaction = async () => {
    const response = await fetch(
      "https://bookish-space-tribble-wr6g55ggrqp4f7xr-8000.app.github.dev/api/transactions",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          amount: Number(amount),
          location: country,
        }),
      }
    );

    const data = await response.json();

    setResult(data);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Detector de Fraude</h1>

      <input
        type="number"
        placeholder="Monto"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />

      <br />
      <br />

      <input
        type="text"
        placeholder="País"
        value={country}
        onChange={(e) => setCountry(e.target.value)}
      />

      <br />
      <br />

      <button onClick={analyzeTransaction}>
        Analizar Transacción
      </button>

      <br />
      <br />

      {result && (
        <div>
          <h2>Resultado</h2>

          <pre>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default App;