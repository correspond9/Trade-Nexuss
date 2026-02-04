import React from 'react';

const LoadingSpinner = ({ 
  size = 'md', 
  color = 'indigo', 
  text = 'Loading...', 
  className = '',
  fullScreen = false 
}) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  };

  const colorClasses = {
    indigo: 'border-indigo-600 border-r-indigo-600',
    gray: 'border-gray-600 border-r-gray-600',
    white: 'border-white border-r-white',
    green: 'border-green-600 border-r-green-600',
    red: 'border-red-600 border-r-red-600',
  };

  const spinner = (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div
        className={`
          animate-spin rounded-full border-2 border-t-transparent border-l-transparent
          ${sizeClasses[size]}
          ${colorClasses[color]}
        `}
      />
      {text && (
        <span className={`mt-2 text-sm ${
          color === 'white' ? 'text-white' : 'text-gray-600'
        }`}>
          {text}
        </span>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white bg-opacity-90 flex items-center justify-center z-50">
        {spinner}
      </div>
    );
  }

  return spinner;
};

// Predefined loading states
export const FullPageLoader = () => (
  <LoadingSpinner size="xl" text="Loading application..." fullScreen />
);

export const TableLoader = ({ colSpan = 6 }) => (
  <tr>
    <td colSpan={colSpan} className="py-8">
      <div className="flex items-center justify-center">
        <LoadingSpinner size="md" text="Loading data..." />
      </div>
    </td>
  </tr>
);

export const CardLoader = ({ height = 'h-32' }) => (
  <div className={`${height} bg-white rounded-lg shadow flex items-center justify-center`}>
    <LoadingSpinner size="md" text="Loading..." />
  </div>
);

export const ButtonLoader = ({ isLoading, children, ...props }) => (
  <button
    {...props}
    disabled={isLoading || props.disabled}
    className={`
      relative inline-flex items-center justify-center
      ${props.className || ''}
      ${isLoading ? 'opacity-75 cursor-not-allowed' : ''}
    `}
  >
    {isLoading && (
      <LoadingSpinner size="sm" color="white" className="mr-2" text="" />
    )}
    {children}
  </button>
);

// Skeleton loaders
export const SkeletonLoader = ({ 
  lines = 3, 
  className = '',
  height = 'h-4',
  width = 'w-full' 
}) => (
  <div className={`space-y-2 ${className}`}>
    {Array.from({ length: lines }).map((_, index) => (
      <div
        key={index}
        className={`${height} ${width} bg-gray-200 rounded animate-pulse`}
        style={{
          animationDelay: `${index * 0.1}s`,
        }}
      />
    ))}
  </div>
);

export const TableSkeletonLoader = ({ 
  rows = 5, 
  columns = 4,
  className = '' 
}) => (
  <div className={`space-y-3 ${className}`}>
    {Array.from({ length: rows }).map((_, rowIndex) => (
      <div key={rowIndex} className="flex space-x-4">
        {Array.from({ length: columns }).map((_, colIndex) => (
          <div
            key={colIndex}
            className="h-4 bg-gray-200 rounded animate-pulse flex-1"
            style={{
              animationDelay: `${(rowIndex * columns + colIndex) * 0.05}s`,
            }}
          />
        ))}
      </div>
    ))}
  </div>
);

export const CardSkeletonLoader = ({ 
  count = 3,
  className = '' 
}) => (
  <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 ${className}`}>
    {Array.from({ length: count }).map((_, index) => (
      <div key={index} className="bg-white rounded-lg shadow p-6 space-y-4">
        <div className="h-6 bg-gray-200 rounded animate-pulse w-3/4" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-full" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-5/6" />
        <div className="h-4 bg-gray-200 rounded animate-pulse w-2/3" />
      </div>
    ))}
  </div>
);

export default LoadingSpinner;