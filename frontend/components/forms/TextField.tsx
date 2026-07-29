import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react';

type Props = {
  label: string;
  error?: string;
  textarea?: boolean;
} & (InputHTMLAttributes<HTMLInputElement> | TextareaHTMLAttributes<HTMLTextAreaElement>);

export function TextField({ label, error, textarea, ...props }: Props) {
  const id = props.id || props.name || label.toLowerCase().replaceAll(' ', '-');
  return (
    <div className="field">
      <label htmlFor={id}>
        {label}
        {props.required ? ' *' : ''}
      </label>
      {textarea ? (
        <textarea id={id} aria-invalid={Boolean(error)} {...(props as TextareaHTMLAttributes<HTMLTextAreaElement>)} />
      ) : (
        <input id={id} aria-invalid={Boolean(error)} {...(props as InputHTMLAttributes<HTMLInputElement>)} />
      )}
      {error ? <span className="error-text">{error}</span> : null}
    </div>
  );
}
