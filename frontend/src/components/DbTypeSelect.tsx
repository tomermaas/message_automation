import { FormControl, InputLabel, MenuItem, Select } from '@mui/material'
import { useSearchParams } from 'react-router-dom'

interface Props {
  value: string
  onChange: (v: string) => void
}

export function DbTypeSelect({ value, onChange }: Props) {
  const [params, setParams] = useSearchParams()

  const handleChange = (event: any) => {
    const v = event.target.value
    const p = new URLSearchParams(params)
    p.set('db_type', v)
    setParams(p)
    onChange(v)
  }

  return (
    <FormControl size="small">
      <InputLabel id="db-type-label">סוג הודעה</InputLabel>
      <Select
        labelId="db-type-label"
        label="סוג הודעה"
        value={value}
        onChange={handleChange}
      >
        <MenuItem value="all">הכל</MenuItem>
        <MenuItem value="distance">מרחק מציון יעד</MenuItem>
      </Select>
    </FormControl>
  )
}
