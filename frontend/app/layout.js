import './globals.css'

export const metadata = {
  title: 'Kora - AI Vision Assistant',
  description: 'AI-powered vision assistance for enhanced spatial awareness',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="theme-color" content="#000000" />
      </head>
      <body className="overflow-hidden">
        {children}
      </body>
    </html>
  )
}
