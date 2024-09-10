import { Input, Loader } from '@openfun/cunningham-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { APIError } from '@/api';
import { parseAPIError } from '@/api/parseAPIError';
import { Box, TextErrors } from '@/components';

interface InputTeamNameProps {
  error: APIError | null;
  isError: boolean;
  isPending: boolean;
  label: string;
  setTeamName: (newTeamName: string) => void;
  defaultValue?: string;
}

export const InputTeamName = ({
  defaultValue,
  error,
  isError,
  isPending,
  label,
  setTeamName,
}: InputTeamNameProps) => {
  const { t } = useTranslation();
  const [isInputError, setIsInputError] = useState(isError);

  const getCauses = (error: APIError): string[] => {
    const handledCauses: string[] = [];
    const unhandledCauses = parseAPIError({
      error,
      errorParams: {
        slug: {
          causes: ['Team with this Slug already exists.'],
          handleError: () => {
            handledCauses.push(
              t(
                'This name is already used for another group. Please enter another one.',
              ),
            );
          },
        },
      },
      serverErrorParams: {
        defaultMessage: t(
          'Your request cannot be processed because the server is experiencing an error. If the problem ' +
            'persists, please contact our support to resolve the issue: suiteterritoriale@anct.gouv.fr',
        ),
      },
    });

    let causes: string[] = [];

    if (handledCauses?.length) {
      causes = [...handledCauses];
    }
    if (unhandledCauses?.length) {
      causes = [...causes, ...unhandledCauses];
    }

    return causes;
  };

  useEffect(() => {
    if (isError) {
      setIsInputError(true);
    }
  }, [isError]);

  const causes = error ? getCauses(error) : undefined;

  return (
    <>
      <Input
        fullWidth
        type="text"
        label={label}
        defaultValue={defaultValue}
        onChange={(e) => {
          setTeamName(e.target.value);
          setIsInputError(false);
        }}
        state={isInputError ? 'error' : 'default'}
      />
      {isError && causes && <TextErrors causes={causes} />}
      {isPending && (
        <Box $align="center">
          <Loader />
        </Box>
      )}
    </>
  );
};
