import { Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/Home';
import { TaskPage } from './pages/Task';

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/task/:id" element={<TaskPage />} />
    </Routes>
  );
}

export default App;
