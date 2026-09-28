import './FilterBar.css'

interface FilterBarProps {
	view: 'positions' | 'people'
	onViewChange: (view: 'positions' | 'people') => void
	department: string | null
	onDepartmentChange: (department: string | null) => void
	departments: string[]
	asOf: string
	onAsOfChange: (asOf: string) => void
}

export function FilterBar({
	view,
	onViewChange,
	department,
	onDepartmentChange,
	departments,
	asOf,
	onAsOfChange,
}: FilterBarProps) {
	const today = new Date().toISOString().slice(0, 10)

	return (
		<div className="filter-bar" role="toolbar" aria-label="Org chart filters">
			<div className="filter-bar__group" role="radiogroup" aria-label="View">
				{(['positions', 'people'] as const).map((option) => (
					<button
						key={option}
						type="button"
						role="radio"
						aria-checked={view === option}
						className={`filter-bar__toggle${view === option ? ' filter-bar__toggle--active' : ''}`}
						onClick={() => {
							onViewChange(option)
						}}
					>
						{option === 'positions' ? 'Positions' : 'People'}
					</button>
				))}
			</div>

			<label className="filter-bar__field">
				<span>Department</span>
				<select
					value={department ?? ''}
					onChange={(event) => {
						onDepartmentChange(event.target.value || null)
					}}
				>
					<option value="">All departments</option>
					{departments.map((dept) => (
						<option key={dept} value={dept}>
							{dept}
						</option>
					))}
				</select>
			</label>

			<label className="filter-bar__field">
				<span>As of</span>
				<input
					type="date"
					value={asOf}
					max={today}
					onChange={(event) => {
						onAsOfChange(event.target.value)
					}}
				/>
			</label>

			{asOf !== today && (
				<button
					type="button"
					className="filter-bar__reset"
					onClick={() => {
						onAsOfChange(today)
					}}
				>
					Today
				</button>
			)}
		</div>
	)
}
