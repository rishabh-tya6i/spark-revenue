import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  variant?: 'standard' | 'glass';
}

const Card: React.FC<CardProps> = ({ 
  children, 
  variant = 'standard', 
  className = '',
  ...props
}) => {
  const variantClass = variant === 'glass' ? 'card-glass' : '';
  
  return (
    <div className={`card ${variantClass} ${className}`} {...props}>
      {children}
    </div>
  );
};

export default Card;
