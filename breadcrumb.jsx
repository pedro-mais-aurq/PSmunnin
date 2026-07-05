import '@/App.css';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import NewSearch from '@/pages/NewSearch';
import SearchDetail from '@/pages/SearchDetail';
import LeadDetail from '@/pages/LeadDetail';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/nova-pesquisa" element={<NewSearch />} />
            <Route path="/pesquisas/:id" element={<SearchDetail />} />
            <Route path="/leads/:id" element={<LeadDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
