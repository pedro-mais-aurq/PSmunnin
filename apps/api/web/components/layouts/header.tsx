import Image from "next/image";
export function Header() {
    return (
        <header className="w-full h-17 border-b flex items-center px-6">
            <Image
                src="/PSmunnin_logo.svg"
                alt="Logo PS Munnin"
                width={40}
                height={40}
                className="dark:invert" />
            <h1 className="text-2xl font-bold">
                PS Munnin
            </h1>
        </header>
    )
}
