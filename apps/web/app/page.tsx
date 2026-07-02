import Image from "next/image";
import { Header } from "@/components/layouts/header";
import { Sidebar } from "@/components/layouts/sidebar";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center bg-zinc-50 font-sans dark:bg-black">

      <Header />
      
      <div className="flex flex min-h-screen">
        <Sidebar />

        <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
    <h1>Conteúdo</h1>

        </main>
      </div>
    </div>

  );
}
