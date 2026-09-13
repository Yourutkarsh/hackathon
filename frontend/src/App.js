import "@/App.css";
import { SocWorkspace } from "@/components/soc/SocWorkspace";
import { Toaster } from "@/components/ui/sonner";

function App() {
  return (
    <div className="App dark">
      <SocWorkspace />
      <Toaster position="top-right" theme="dark" richColors closeButton />
    </div>
  );
}

export default App;
