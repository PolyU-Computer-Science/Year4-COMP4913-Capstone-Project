interface PageHeadingProps {
  title: string
  subtitle?: string
}

export function PageHeading({ title, subtitle }: PageHeadingProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <h1 className="text-2xl font-bold text-foreground">{title}</h1>
      {subtitle ? (
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      ) : null}
    </div>
  )
}
